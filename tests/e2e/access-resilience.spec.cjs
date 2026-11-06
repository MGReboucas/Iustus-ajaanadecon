const { test, expect } = require('../../frontend/node_modules/@playwright/test');

const context = { csrfToken: 'synthetic-csrf', portal: 'team', policyVersion: 'test', mfaRequired: false, registrationAvailable: false };
const unavailable = { status: 503, json: { error: { code: 'SERVICE_UNAVAILABLE', message: 'Serviço temporariamente indisponível.' } } };

test('convite continua editável offline e recupera sem perder o token ou os dados', async ({ page }) => {
  let online = false;
  await page.route('**/api/v1/auth/csrf', route => route.fulfill(online ? { json: context } : unavailable));
  let submitted;
  await page.route('**/api/v1/auth/invitations/accept', async route => {
    submitted = route.request().postDataJSON();
    await route.fulfill({ status: 201, json: { message: 'Conta ativada.' } });
  });
  await page.goto('/acessar#invite=synthetic-invite');
  await page.getByLabel('Nome completo').fill('Advogado Teste');
  await page.getByLabel('Senha', { exact: true }).fill('Synthetic-Passphrase-938!');
  await expect(page.getByRole('status')).toContainText('Você pode preencher');
  await page.getByRole('button', { name: 'Aceitar convite' }).click();
  await expect(page.locator('.auth-error[role="alert"]')).toContainText('temporariamente indisponível');
  await expect(page.getByLabel('Nome completo')).toHaveValue('Advogado Teste');
  await expect(page.getByLabel('Senha', { exact: true })).toBeEnabled();
  online = true;
  await page.getByRole('button', { name: 'Aceitar convite' }).click();
  await expect(page.getByRole('status')).toContainText('Conta ativada');
  expect(submitted).toEqual({ token: 'synthetic-invite', name: 'Advogado Teste', password: 'Synthetic-Passphrase-938!' });
});

test('a consulta inicial lenta não bloqueia digitação nem navegação', async ({ page }) => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  await page.route('**/api/v1/auth/csrf', async route => { await pending; await route.fulfill({ json: context }); });
  await page.goto('/acessar');
  await page.getByLabel('E-mail', { exact: true }).fill('synthetic@example.test');
  await page.getByLabel('Senha', { exact: true }).fill('Synthetic-Passphrase-938!');
  await expect(page.getByRole('button', { name: 'Acessar plataforma' })).toBeEnabled();
  await page.getByRole('button', { name: 'Esqueci minha senha' }).click();
  await expect(page.getByLabel('E-mail', { exact: true })).toHaveValue('synthetic@example.test');
  release();
});

test('repete a consulta segura após 503 mas nunca repete o envio do formulário', async ({ page }) => {
  let reads = 0, posts = 0;
  await page.route('**/api/v1/auth/csrf', route => route.fulfill(++reads === 1 ? unavailable : { json: context }));
  await page.route('**/api/v1/auth/invitations/accept', async route => { posts++; await route.fulfill(unavailable); });
  await page.goto('/acessar#invite=synthetic-invite');
  await expect.poll(() => reads).toBe(2);
  await page.getByLabel('Nome completo').fill('Advogado Teste');
  await page.getByLabel('Senha', { exact: true }).fill('Synthetic-Passphrase-938!');
  await page.getByRole('button', { name: 'Aceitar convite' }).click();
  await expect(page.locator('.auth-error[role="alert"]')).toBeVisible();
  expect(posts).toBe(1);
  await expect(page.getByLabel('Nome completo')).toBeEnabled();
  await expect(page.getByLabel('Senha', { exact: true })).toHaveValue('Synthetic-Passphrase-938!');
});
