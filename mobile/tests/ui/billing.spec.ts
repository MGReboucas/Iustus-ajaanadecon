import { test, expect } from '@playwright/test';

const user = { id: '00000000-0000-0000-0000-000000000101', name: 'Pessoa Teste', email: 'buyer@example.test', role: 'CLIENT', caseEmailEnabled: true };
const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization,content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };

test('app abre checkout no portal e permite cancelar a próxima renovação com bearer', async ({ page, context }) => {
  let canceled = false;
  await context.route('https://mobile-api.example.test/checkout', route => route.fulfill({ contentType: 'text/html', body: '<h1>Checkout Mercado Pago</h1>' }));
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', async route => {
    const req = route.request(); const path = new URL(req.url()).pathname.split('/mobile/')[1];
    const reply = (json: unknown) => route.fulfill({ headers, json });
    if (req.method() === 'OPTIONS') return route.fulfill({ headers, status: 204 });
    if (path === 'auth/login') return reply({ token: 'x'.repeat(43), expiresAt: new Date(Date.now() + 86400000).toISOString(), user });
    if (path === 'me') return reply({ user });
    if (path === 'auth/context') return reply({ policyVersion: 'test', registrationAvailable: false, billingAvailable: true, checkoutAvailable: true });
    if (path === 'billing/plan') return reply({ provider: 'mercadopago', automaticRenewal: true, amount: 69990, installments: 10, available: true, sandbox: true, planVersion: 'v3', policyVersion: 'test' });
    if (path === 'billing/subscription') {
      expect(req.headers().authorization).toBe('Bearer ' + 'x'.repeat(43));
      if (req.method() === 'POST') { expect(req.postDataJSON()).toEqual({ cancelRenewal: true }); canceled = true; }
      return reply({ subscription: { status: canceled ? 'CANCELED' : 'ACTIVE', automaticRenewal: !canceled,
        nextChargeAt: canceled ? null : '2027-11-04T12:00:00Z', amount: 69990, installments: 10,
        canceledAt: canceled ? '2026-11-04T12:00:00Z' : null } });
    }
    if (path === 'dashboard') return reply({ user, totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [], membership: { active: true, expiresAt: '2027-11-04T12:00:00Z' }, submission: { canSubmit: true, mode: 'MEMBERSHIP', message: 'Associação ativa' } });
    return reply({ results: [], nextCursor: null });
  });
  await page.goto('/');
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByLabel('Senha', { exact: true }).fill('synthetic');
  await page.getByRole('button', { name: 'Entrar na minha conta' }).click();
  await expect(page.getByText('Olá, Pessoa.')).toBeVisible();
  await page.getByRole('tab', { name: /Minha conta/ }).click();
  await page.getByRole('button', { name: 'Opções da associação' }).click();
  await expect(page.getByText('Renovação automática ativa', { exact: true })).toBeVisible();
  const popupPromise = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Pagar com Mercado Pago no portal' }).click();
  const popup = await popupPromise;
  await expect(popup).toHaveURL('https://mobile-api.example.test/checkout');
  await popup.close();
  await expect(page.getByRole('button', { name: 'Cancelar próxima renovação' })).toBeDisabled();
  await page.getByRole('switch', { name: 'Confirmar cancelamento da renovação' }).check();
  await page.getByRole('button', { name: 'Cancelar próxima renovação' }).click();
  await expect(page.getByText('Próxima renovação cancelada', { exact: true })).toBeVisible();
  expect(canceled).toBe(true);
});

test('app não oferece pagamento quando o provedor não está habilitado', async ({ page }) => {
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', route => route.fulfill({ headers, json:
    route.request().url().endsWith('/billing/plan') ? { amount: 69990, installments: 10, available: false, sandbox: true } :
    { policyVersion: 'test', registrationAvailable: false, billingAvailable: false, checkoutAvailable: true } }));
  await page.goto('/membership');
  await expect(page.getByText(/A adesão pelo aplicativo ainda não está disponível/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pagar com Mercado Pago no portal' })).toHaveCount(0);
});
