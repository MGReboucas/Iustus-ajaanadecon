const { test, expect } = require('../../frontend/node_modules/@playwright/test');
const path = require('node:path');

// Dados sintéticos; o teste nunca envia cartões ou cobranças ao PagBank.
async function setup(page, { offline = false, declined = false, uncertain = false, keyFailure = false } = {}) {
  const requests = [];
  let submitted = false;
  await page.route('https://assets.pagseguro.com.br/**', route => route.fulfill({ contentType: 'application/javascript', body: 'window.PagSeguro = { encryptCard: () => ({ hasErrors: false, encryptedCard: "A".repeat(344) }) };' }));
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const endpoint = new URL(request.url()).pathname.split('/api/v1/')[1];
    if (endpoint === 'billing/plan') return offline ? route.fulfill({ status: 503, json: {} }) : route.fulfill({ json: { amount: 69990, installments: 10, available: true, sandbox: true } });
    if (endpoint === 'billing/card-key') return route.fulfill(keyFailure ? { status: 503, json: {} } : { json: { publicKey: 'public-test-key' } });
    if (endpoint === 'auth/csrf') return route.fulfill({ json: { csrfToken: 'synthetic-csrf' } });
    if (endpoint === 'billing/checkout') {
      if (request.method() === 'POST') {
        requests.push({ key: request.headers()['idempotency-key'], body: request.postDataJSON() });
        submitted = true;
        if (uncertain && requests.length === 1) return route.fulfill({ status: 502, json: { error: { code: 'UPSTREAM_ERROR', message: 'Falha de comunicação.' } } });
        return route.fulfill({ json: { status: 'WAITING' } });
      }
      if (!submitted) return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND' } } });
      return route.fulfill({ json: { status: uncertain && requests.length === 1 ? 'CREATING' : declined ? 'DECLINED' : 'PAID' } });
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
  await page.getByLabel('Número do cartão').fill('4111 1111 1111 1111');
  await page.getByLabel('Validade (MM/AA)', { exact: true }).fill('12/39');
  await page.getByLabel('Código de segurança (CVV)').fill('123');
  await page.getByLabel(/Entendi que cada ocorrência/).check();
}

test('preço e formulário aparecem mesmo com API indisponível', async ({ page }) => {
  await setup(page, { offline: true });
  await page.goto('/checkout');
  await expect(page.locator('.summary-price strong')).toHaveText(/69,99/);
  await expect(page.getByLabel('E-mail do associado', { exact: true })).toBeVisible();
  await expect(page.getByLabel('CPF do associado', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Número do cartão')).toBeVisible();
  await expect(page.getByRole('button', { name: /Pagar · 10x de/ })).toBeDisabled();
  await expect(page.locator('.mp-error[role=alert]')).toBeVisible();
  await expect(page.getByText(/Continuar no PagBank/)).toHaveCount(0);
});

test('cadastro e cartão de terceiro são enviados separadamente e sem dados abertos do cartão', async ({ page }) => {
  const requests = await setup(page);
  await page.goto('/checkout');
  await fill(page);
  await page.getByLabel('O cartão está no nome do associado.').uncheck();
  await page.getByLabel('Nome do titular do cartão').fill('Titular Teste');
  await page.getByLabel('CPF do titular do cartão').fill('52998224725');
  await page.getByRole('button', { name: /Pagar · 10x de/ }).click();
  await expect(page.getByRole('heading', { name: 'Sua associação está ativa' })).toBeVisible();
  expect(new URL(page.url()).pathname).toBe('/checkout');
  expect(requests).toHaveLength(1);
  expect(requests[0].body).toEqual({ accepted: true, customer: { name: 'Associado Teste', email: 'buyer@example.test', cpf: '12345678909', phone: '11999999999' }, card: { encrypted: 'A'.repeat(344), holderName: 'Titular Teste', holderCpf: '52998224725' } });
  expect(JSON.stringify(requests)).not.toContain('4111111111111111');
  expect(JSON.stringify(requests)).not.toContain('cvv');
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }));
  for (const sensitive of ['buyer@example.test', '12345678909', '4111', 'A'.repeat(344)]) expect(stored).not.toContain(sensitive);
});

test('CPF inválido e confirmação de e-mail divergente impedem cobrança', async ({ page }) => {
  const requests = await setup(page);
  await page.goto('/checkout'); await fill(page);
  await page.getByLabel('CPF do associado', { exact: true }).fill('11111111111');
  await page.getByRole('button', { name: /Pagar · 10x de/ }).click();
  await expect(page.locator('.mp-error[role=alert]')).toHaveText('Informe um CPF válido para o associado.');
  await page.getByLabel('CPF do associado', { exact: true }).fill('12345678909');
  await page.getByLabel('Confirme seu e-mail').fill('different@example.test');
  await page.getByRole('button', { name: /Pagar · 10x de/ }).click();
  await expect(page.locator('.mp-error[role=alert]')).toContainText('Os e-mails devem ser iguais');
  expect(requests).toHaveLength(0);
});

test('falha de comunicação repete a mesma referência e o mesmo cartão criptografado', async ({ page }) => {
  const requests = await setup(page, { uncertain: true });
  await page.goto('/checkout'); await fill(page);
  await page.getByRole('button', { name: /Pagar · 10x de/ }).click();
  await expect(page.getByRole('button', { name: 'Reenviar a mesma tentativa' })).toBeVisible();
  await page.getByRole('button', { name: 'Reenviar a mesma tentativa' }).click();
  await expect(page.getByRole('heading', { name: 'Sua associação está ativa' })).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[0]).toEqual(requests[1]);
});

test('cartão recusado permite outra tentativa com nova referência', async ({ page }) => {
  const requests = await setup(page, { declined: true });
  await page.goto('/checkout'); await fill(page);
  await page.getByRole('button', { name: /Pagar · 10x de/ }).click();
  await expect(page.getByText(/O cartão não foi aprovado/)).toBeVisible();
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await fill(page);
  await page.getByRole('button', { name: /Pagar · 10x de/ }).click();
  await expect(page.getByText(/O cartão não foi aprovado/)).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[1].key).not.toBe(requests[0].key);
});

test('falha na chave pública bloqueia envio do cartão', async ({ page }) => {
  const requests = await setup(page, { keyFailure: true });
  await page.goto('/checkout'); await fill(page);
  await expect(page.getByRole('button', { name: /Pagar · 10x de/ })).toBeDisabled();
  await expect(page.locator('.mp-error[role=alert]')).toBeVisible();
  expect(requests).toHaveLength(0);
});

test('checkout cabe na tela do celular e mantém preço e cadastro visíveis', async ({ page }) => {
  await setup(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/checkout');
  await expect(page.locator('.summary-price strong')).toHaveText(/69,99/);
  await expect(page.getByLabel('Nome completo', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(__dirname, '../../.local/checkout-integrated-mobile.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: path.join(__dirname, '../../.local/checkout-integrated-desktop.png'), fullPage: true });
});
