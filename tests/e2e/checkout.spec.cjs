const { test, expect } = require('../../frontend/node_modules/@playwright/test');
const path = require('node:path');

const plan = { provider: 'mercadopago', automaticRenewal: false, amount: 69990, installments: 10, planVersion: 'annual-2026-v5-mp-manual', policyVersion: 'test-v1', available: true, sandbox: true };
test('retained sandbox review can be archived with confirmation and opens a fresh form', async ({ page }) => {
  let reset = false;
  await page.route('**/api/v1/**', route => {
    const endpoint = new URL(route.request().url()).pathname.split('/api/v1/')[1];
    if (endpoint === 'billing/plan') return route.fulfill({ json: plan });
    if (endpoint === 'billing/card-key') return route.fulfill({ json: { publicKey: 'synthetic' } });
    if (endpoint === 'auth/csrf') return route.fulfill({ json: { csrfToken: 'synthetic' } });
    if (endpoint === 'billing/checkout/reset-test') {
      expect(route.request().postDataJSON()).toEqual({ confirm: true });
      reset = true;
      return route.fulfill({ json: { reset: true } });
    }
    return route.fulfill(reset ? { status: 404, json: {} } : { json: { status: 'REVIEW_AMOUNT' } });
  });
  await page.goto('/#checkout');
  await expect(page.getByText(/divergem do plano contratado/)).toBeVisible();
  await page.getByRole('button', { name: 'Encerrar tentativa e iniciar novo teste' }).click();
  expect(reset).toBe(false);
  await page.getByRole('button', { name: 'Confirmar novo teste' }).click();
  await expect(page.getByLabel('Nome completo', { exact: true })).toBeVisible();
  expect(reset).toBe(true);
});
async function setup(page, { offline = false, declined = false, uncertain = false, keyFailure = false, pending = false, interest = false } = {}) {
  const requests = []; let submitted = false;
  await page.route('https://sdk.mercadopago.com/**', route => route.fulfill({ contentType: 'application/javascript', body: `window.MercadoPago = class { cardForm(options) {
    window.cardFormOptions = options;
    const form = document.getElementById(options.form.id);
    const select = document.getElementById(options.form.installments.id);
    for (const name of ['issuer', 'identificationType']) document.getElementById(options.form[name].id).innerHTML = '<option value="25">Teste</option>';
    const costs = [{ installments: 1, installment_amount: 699.9, total_amount: 699.9 }, { installments: 10, installment_amount: ${interest ? 84.44 : 69.99}, total_amount: ${interest ? 844.43 : 699.9} }, { installments: 12, installment_amount: 84.44, total_amount: 844.43 }];
    const handler = event => { event.preventDefault(); options.callbacks.onSubmit(event); };
    form.addEventListener('submit', handler);
    setTimeout(() => {
      options.callbacks.onInstallmentsReceived(null, { payer_costs: costs });
      select.innerHTML = '<option value="">Selecione</option><option value="1">1x de R$ 699,90</option><option value="10">10x de R$ 69,99</option><option value="12">12x com juros</option>';
      options.callbacks.onReady();
    }, 10);
    return { getCardFormData: () => ({ token: 'synthetic-token-123456', paymentMethodId: 'visa', issuerId: '25', installments: select.value }), unmount: () => form.removeEventListener('submit', handler) };
  } };` }));
  await page.route('**/api/v1/**', async route => {
    const req = route.request(); const endpoint = new URL(req.url()).pathname.split('/api/v1/')[1];
    if (endpoint === 'billing/plan') return route.fulfill(offline ? { status: 503, json: {} } : { json: plan });
    if (endpoint === 'billing/card-key') return route.fulfill(keyFailure ? { status: 503, json: {} } : { json: { publicKey: 'synthetic-public' } });
    if (endpoint === 'auth/csrf') return route.fulfill({ json: { csrfToken: 'synthetic' } });
    if (endpoint === 'billing/checkout') {
      if (req.method() === 'POST') {
        requests.push({ key: req.headers()['idempotency-key'], body: req.postDataJSON() }); submitted = true;
        if (uncertain && requests.length === 1) return route.fulfill({ status: 502, json: { error: { code: 'UPSTREAM_ERROR', message: 'Falha de comunicação.' } } });
        return route.fulfill({ json: { status: 'WAITING' } });
      }
      if (!submitted) return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND' } } });
      return route.fulfill({ json: { status: uncertain && requests.length === 1 ? 'CREATING' : declined ? 'DECLINED' : pending ? 'WAITING' : 'PAID' } });
    }
    return route.fulfill({ status: 404, json: {} });
  });
  return requests;
}
async function fill(page) {
  await page.getByLabel('Nome completo', { exact: true }).fill('Associado Teste');
  await page.getByLabel('E-mail do associado', { exact: true }).fill('buyer@example.test');
  await page.getByLabel('Confirme seu e-mail').fill('buyer@example.test');
  await page.getByLabel('CPF do associado', { exact: true }).fill('123.456.789-09');
  await page.getByLabel('Celular com DDD').fill('11999999999');
  await page.getByLabel('Nome impresso no cartão').fill('APRO');
  await page.getByLabel('Documento do titular', { exact: true }).fill('12345678909');
  await page.getByLabel('Quantidade de parcelas').selectOption('10');
  await page.getByLabel(/Autorizo a compra anual/).check();
}
async function pay(page) {
  await page.getByRole('button', { name: 'Pagar R$ 699,90' }).click();
}

test('API indisponível mantém oferta visível e bloqueia cobrança', async ({ page }) => {
  await setup(page, { offline: true }); await page.goto('/#checkout');
  await expect(page.locator('.summary-price strong')).toHaveText(/699,90/);
  await expect(page.getByRole('button', { name: 'Pagar R$ 699,90' })).toHaveCount(0);
  await expect(page.locator('.mp-error')).toBeVisible();
});

test('juros são bloqueados antes do pagamento e cadastro e cartão aparecem juntos', async ({ page }) => {
  const requests = await setup(page, { interest: true });
  await page.goto('/#checkout');
  await expect(page.getByLabel('Nome completo', { exact: true })).toBeVisible();
  await expect(page.locator('#iustus-card-number')).toBeVisible();
  await expect(page.locator('#iustus-installments option[value="10"]')).toHaveAttribute('disabled', '');
  await page.getByLabel('Quantidade de parcelas').selectOption('1');
  await expect(page.locator('.checkout-total')).toContainText('1x de R$ 699,90');
  await expect(page.locator('.checkout-total')).not.toContainText('844');
  expect(requests).toHaveLength(0);
});
test('Mercado Pago recebe token, consentimento e oferta; dados de cartão ficam fora da API', async ({ page }) => {
  const requests = await setup(page); await page.goto('/#checkout'); await fill(page); await pay(page);
  await expect(page.getByRole('heading', { name: 'Sua associação está ativa' })).toBeVisible();
  expect(requests).toHaveLength(1);
  expect(requests[0].body).toEqual({ accepted: true, automaticRenewal: false, planVersion: plan.planVersion, policyVersion: plan.policyVersion,
    customer: { name: 'Associado Teste', email: 'buyer@example.test', cpf: '12345678909', phone: '11999999999' },
    card: { token: 'synthetic-token-123456', paymentMethodId: 'visa', issuerId: '25', installments: 10 } });
  await expect(page).toHaveURL(/checkout\/resultado/);
  expect(await page.evaluate(() => window.cardFormOptions?.iframe)).not.toBe(false);
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }));
  for (const sensitive of ['buyer@example.test', '12345678909', 'synthetic-token']) expect(stored).not.toContain(sensitive);
});
test('CPF inválido e e-mails divergentes impedem preparação do cartão', async ({ page }) => {
  const requests = await setup(page); await page.goto('/#checkout'); await fill(page);
  await page.getByLabel('CPF do associado', { exact: true }).fill('11111111111');
  await page.getByRole('button', { name: 'Pagar R$ 699,90' }).click();
  await expect(page.locator('.mp-error')).toContainText('CPF válido');
  await page.getByLabel('CPF do associado', { exact: true }).fill('12345678909');
  await page.getByLabel('Confirme seu e-mail').fill('different@example.test');
  await page.getByRole('button', { name: 'Pagar R$ 699,90' }).click();
  await expect(page.locator('.mp-error')).toContainText('Os e-mails devem ser iguais');
  expect(requests).toHaveLength(0);
});
test('falha de comunicação repete exatamente a tentativa original', async ({ page }) => {
  const requests = await setup(page, { uncertain: true }); await page.goto('/#checkout'); await fill(page); await pay(page);
  await page.getByRole('button', { name: 'Reenviar a mesma tentativa' }).click();
  await expect(page.getByRole('heading', { name: 'Sua associação está ativa' })).toBeVisible();
  expect(requests).toHaveLength(2); expect(requests[0]).toEqual(requests[1]);
});
test('cartão recusado permite nova tentativa com referência diferente', async ({ page }) => {
  const requests = await setup(page, { declined: true }); await page.goto('/#checkout'); await fill(page); await pay(page);
  await expect(page.getByText(/O cartão não foi aprovado/)).toBeVisible();
  await page.getByRole('button', { name: 'Tentar novamente' }).click(); await fill(page); await pay(page);
  await expect(page.getByText(/O cartão não foi aprovado/)).toBeVisible();
  expect(requests).toHaveLength(2); expect(requests[0].key).not.toBe(requests[1].key);
});
test('falha na configuração impede cobrança', async ({ page }) => {
  const requests = await setup(page, { keyFailure: true }); await page.goto('/#checkout');
  await expect(page.getByRole('button', { name: 'Pagar R$ 699,90' })).toHaveCount(0); expect(requests).toHaveLength(0);
});
test('retorno forjado nunca exibe associação ativa', async ({ page }) => {
  await setup(page, { pending: true }); await page.goto('/?status=approved&payment_id=987#checkout'); await fill(page); await pay(page);
  await expect(page.getByText('Pagamento enviado. Aguardando confirmação do Mercado Pago.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sua associação está ativa' })).toHaveCount(0);
});
test('layout móvel e oferta anual preservados', async ({ page }) => {
  await setup(page); await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/#checkout');
  await expect(page.locator('.summary-price strong')).toHaveText(/699,90/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(__dirname, '../../.local/checkout-mercadopago-mobile.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(__dirname, '../../.local/checkout-mercadopago-desktop.png'), fullPage: true });
});
test('plano inválido bloqueia pagamento', async ({ page }) => {
  await setup(page); await page.route('**/api/v1/billing/plan', route => route.fulfill({ json: { ...plan, installments: 0 } }));
  await page.goto('/#checkout'); await expect(page.getByRole('button', { name: 'Pagar R$ 699,90' })).toHaveCount(0);
});
test('pagamento confirmado permanece ativo ao reabrir checkout', async ({ page }) => {
  await setup(page); await page.route('**/api/v1/billing/checkout', route => route.fulfill({ json: { status: 'PAID' } }));
  await page.goto('/#checkout'); await expect(page.getByRole('heading', { name: 'Sua associação está ativa' })).toBeVisible();
});
test('rota checkout mantém o redirecionamento para a landing', async ({ page }) => {
  await setup(page); await page.goto('/checkout'); await expect(page).toHaveURL(/\/#checkout$/);
});


test('painel Next informa renovação manual sem botão de cobrança', async ({ page }) => {
  let canceled = false;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/**', async route => {
    const request = route.request(); const endpoint = new URL(request.url()).pathname.split('/api/v1/')[1];
    if (endpoint === 'dashboard/client') return route.fulfill({ json: { user: { id: 'customer-id', role: 'CLIENT', name: 'Associado Teste', email: 'buyer@example.test', caseEmailEnabled: true } } });
    if (endpoint === 'dashboard/overview') return route.fulfill({ json: { totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [], submission: null } });
    if (endpoint === 'cases/catalog') return route.fulfill({ json: { categories: [], states: [], submission: null, documentsAvailable: false, intakeRequired: false } });
    if (endpoint === 'auth/csrf') return route.fulfill({ json: { csrfToken: 'synthetic' } });
    if (endpoint === 'billing/subscription') {
      if (request.method() === 'POST') {
        expect(request.postDataJSON()).toEqual({ cancelRenewal: true });
        expect(request.headers()['x-csrftoken']).toBe('synthetic'); canceled = true;
      }
      return route.fulfill({ json: { subscription: { status: canceled ? 'CANCELED' : 'ACTIVE', automaticRenewal: !canceled,
        nextChargeAt: canceled ? null : '2027-11-04T12:00:00Z', amount: 69990, installments: 10,
        canceledAt: canceled ? '2026-11-04T12:00:00Z' : null } } });
    }
    return route.fulfill({ json: { results: [], nextCursor: null } });
  });
  await page.goto('/cliente#minha-conta');
  await expect(page.getByText('Sua adesão não tem renovação automática.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancelar próxima renovação' })).toHaveCount(0);
  expect(canceled).toBe(false); expect(errors).toEqual([]);
});
