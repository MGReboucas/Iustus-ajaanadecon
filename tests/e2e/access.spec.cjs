const { test, expect } = require('../../frontend/node_modules/@playwright/test');
const { execFileSync } = require('node:child_process');
const { createHmac, randomUUID } = require('node:crypto');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const python = process.env.IUSTUS_TEST_PYTHON || path.join(root, 'backend', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const password = 'Synthetic-Browser-Passphrase-938!';
const teamOrigin = 'http://localhost:3000';
function fixture(action, email) {
  return JSON.parse(execFileSync(python, [path.join(__dirname, 'fixture.py'), action, email], { encoding: 'utf8', windowsHide: true, timeout: 15000 }));
}
function mailLink(email) { return fixture('mail', email).body.match(/http[^\s]+/)[0]; }
function email() { return `e2e-${randomUUID()}@example.test`; }
function otp(secret) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  const bits = [...secret].map(c => alphabet.indexOf(c).toString(2).padStart(5, '0')).join('');
  const key = Buffer.from((bits.match(/.{8}/g) || []).map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const hash = createHmac('sha1', key).update(counter).digest();
  const offset = hash[hash.length - 1] & 15;
  return String((hash.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, '0');
}
async function signIn(page, origin, address, secret = password) {
  await page.goto(origin + '/acessar');
  await page.getByLabel('E-mail', { exact: true }).fill(address);
  await page.getByLabel('Senha', { exact: true }).fill(secret);
  await page.getByRole('button', { name: 'Acessar plataforma' }).click();
}
async function enroll(page) {
  const secret = await page.getByTestId('mfa-secret').textContent();
  await page.getByLabel('Código do autenticador', { exact: true }).fill(otp(secret));
  await page.getByRole('button', { name: 'Confirmar segundo fator' }).click();
  await expect(page.getByRole('heading', { name: 'Guarde seus códigos de recuperação' })).toBeVisible();
  const codes = await page.locator('.recovery-codes li code').allTextContents();
  await page.getByRole('button', { name: 'Guardei os códigos. Continuar' }).click();
  await expect(page).toHaveURL(/\/advogado$/);
  return codes;
}

test('administrador confirma MFA, convida advogado e usa recuperação uma vez', async ({ browser }) => {
  const admin = email(), lawyer = email();
  fixture('admin', admin);
  const context = await browser.newContext();
  const page = await context.newPage();
  await signIn(page, teamOrigin, admin);
  const codes = await enroll(page);
  await page.getByLabel('E-mail do profissional').fill(lawyer);
  await page.getByRole('button', { name: 'Aprovar e enviar ativação' }).click();
  await expect(page.getByRole('status')).toContainText('convite');
  const other = await browser.newContext();
  const professional = await other.newPage();
  await professional.goto(mailLink(lawyer));
  await professional.getByLabel('Nome completo').fill('Advogado de Teste');
  await professional.getByLabel('Senha', { exact: true }).fill(password);
  await professional.getByRole('button', { name: 'Aceitar convite' }).click();
  await expect(professional.getByRole('status')).toContainText('Convite aceito');
  await signIn(professional, teamOrigin, lawyer);
  await enroll(professional);
  await expect(professional.getByRole('heading', { name: 'Olá, Advogado de Teste.' })).toBeVisible();
  await expect(professional.getByRole('heading', { name: 'Aprovar profissional' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await expect(page).toHaveURL(/\/acessar$/);
  await signIn(page, teamOrigin, admin);
  await page.getByLabel('Código do autenticador ou de recuperação').fill(codes[0]);
  await page.getByRole('button', { name: 'Confirmar segundo fator' }).click();
  await expect(page.getByRole('heading', { name: 'Olá, Admin Teste.' })).toBeVisible();
  await page.getByRole('button', { name: 'Atualizar usuários' }).click();
  const row = page.locator('.account-management li').filter({ hasText: lawyer });
  await row.getByRole('button', { name: 'Revogar acesso', exact: true }).click();
  await page.getByLabel('Motivo da alteração').fill('Revogação sintética de acesso da equipe.');
  await page.getByRole('button', { name: 'Confirmar alteração de acesso' }).click();
  await expect(row).toContainText('Acesso revogado');
  await professional.reload();
  await expect(professional).toHaveURL(/\/acessar$/);
  await other.close(); await context.close();
});


test('endereço único bloqueia cadastro público, cliente e headers forjados', async ({ page, request }) => {
  await page.goto(teamOrigin);
  await expect(page).toHaveURL(/\/acessar$/);
  await expect(page.getByRole('button', { name: 'Criar conta', exact: true })).toHaveCount(0);
  await page.goto(teamOrigin + '/cliente');
  await expect(page).toHaveURL(/\/acessar$/);
  const address = email();
  fixture('client', address);
  await signIn(page, teamOrigin, address);
  await expect(page.locator('.auth-error')).toContainText('Não foi possível entrar');
  const csrf = await request.get(teamOrigin + '/api/v1/auth/csrf', {
    headers: { 'X-Forwarded-Host': 'evil.invalid', 'X-Iustus-Portal-Host': 'evil.invalid', 'X-Iustus-Proxy-Key': 'forged' },
  });
  expect((await csrf.json()).portal).toBe('team');
  const login = await request.post(teamOrigin + '/api/v1/auth/login', { data: { email: email(), password } });
  expect(login.status()).toBe(403);
  expect((await login.json()).error.code).toBe('CSRF_FAILED');
  expect((await request.get(teamOrigin + '/api/v1/dashboard/team')).status()).toBe(403);
});
