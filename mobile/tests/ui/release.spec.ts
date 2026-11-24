import { test, expect } from '@playwright/test';

const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization,content-type', 'access-control-allow-methods': 'GET,POST,PATCH,OPTIONS' };
const id = '00000000-0000-0000-0000-000000000001';
const user = { id, name: 'Pessoa Teste', email: 'release@example.test', role: 'CLIENT', caseEmailEnabled: true };
const dashboard = { user, totalCases: 0, attentionCount: 0, unreadCount: 1, states: [], attentionCases: [], recentActivity: [], membership: { active: true, expiresAt: '2099-01-01' }, submission: { canSubmit: true } };

for (const mode of ['reset', 'member'] as const) {
  test(`complete ${mode} access and reject mismatched password`, async ({ page }) => {
    let submitted = false;
    await page.route('https://mobile-api.example.test/api/v1/mobile/**', async route => {
      if (route.request().method() === 'OPTIONS') return route.fulfill({ headers, status: 204 });
      expect(route.request().url()).toContain(mode === 'member' ? 'billing/activate' : 'auth/reset');
      expect(route.request().postDataJSON()).toEqual({ token: 'a'.repeat(43), password: 'Synthetic-938!', ...(mode === 'member' ? { name: 'Pessoa Teste' } : {}) });
      submitted = true; return route.fulfill({ headers, status: 204 });
    });
    await page.goto('/access');
    await page.getByLabel('Link recebido por e-mail').fill(`https://mobile-api.example.test/acessar#${mode}=${'a'.repeat(43)}`);
    if (mode === 'member') await page.getByLabel('Nome completo').fill('Pessoa Teste');
    await page.getByLabel('Nova senha', { exact: true }).fill('Synthetic-938!');
    await page.getByLabel('Confirmar nova senha').fill('different');
    await page.getByRole('button', { name: 'Confirmar acesso' }).click();
    await expect(page.getByRole('alert')).toContainText('confirme a mesma senha');
    expect(submitted).toBe(false);
    await page.getByLabel('Confirmar nova senha').fill('Synthetic-938!');
    await page.getByRole('button', { name: 'Confirmar acesso' }).click();
    await expect(page.getByText('Acesso atualizado. Entre com seu e-mail e senha.')).toBeVisible();
    expect(submitted).toBe(true);
  });
}

test('membership retries after network failure', async ({ page }) => {
  let offline = true;
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', route => offline ? route.abort() : route.fulfill({ headers, json:
    route.request().url().endsWith('auth/context') ? { checkoutAvailable: false, billingAvailable: false } : { available: false } }));
  await page.goto('/membership');
  await expect(page.getByRole('alert')).toContainText('Não foi possível conectar');
  offline = false;
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(page.getByText(/A adesão pelo aplicativo ainda não está disponível/)).toBeVisible();
});

test('refresh invalidates old notice pages; account update and deletion request', async ({ page }) => {
  let refreshed = false; let saved = false; let deleted = false;
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', async route => {
    const req = route.request(); const url = new URL(req.url()); const path = url.pathname.split('/mobile/')[1];
    const reply = (json: unknown, status = 200) => route.fulfill({ headers, json, status });
    if (req.method() === 'OPTIONS') return route.fulfill({ headers, status: 204 });
    if (path === 'auth/login') return reply({ token: 'x'.repeat(43), expiresAt: new Date(Date.now() + 86400000).toISOString(), user });
    expect(req.headers().authorization).toBe('Bearer ' + 'x'.repeat(43));
    if (path === 'dashboard') return reply(dashboard);
    if (path === 'notifications') {
      const more = url.searchParams.has('cursor');
      return reply({ results: [{ id: more ? 'old-page' : id, caseId: id, title: more ? 'Aviso antigo paginado' : refreshed ? 'Aviso atualizado' : 'Aviso inicial', reference: '1', createdAt: '2026-11-09T12:00:00Z', readAt: null }], nextCursor: more || refreshed ? null : 'next' });
    }
    if (path === 'me') { expect(req.method()).toBe('PATCH'); expect(req.postDataJSON()).toEqual({ name: 'Nome atualizado', caseEmailEnabled: false }); saved = true; return reply({ user }); }
    if (path === 'privacy/requests') {
      if (req.method() === 'POST') { expect(req.postDataJSON().kind).toBe('DELETION'); expect(req.postDataJSON().description.length).toBeGreaterThan(10); deleted = true; return reply({ id }, 201); }
      return reply({ results: [], nextCursor: null });
    }
    throw new Error('Unexpected route: ' + path);
  });
  await page.goto('/');
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByLabel('Senha', { exact: true }).fill('synthetic');
  await page.getByRole('button', { name: 'Entrar na minha conta' }).click();
  await page.getByRole('tab', { name: /Avisos/ }).click();
  await page.getByRole('button', { name: 'Mais avisos' }).click();
  await expect(page.getByText('Aviso antigo paginado')).toBeVisible();
  await page.getByRole('tab', { name: /Minha conta/ }).click();
  refreshed = true;
  await page.getByRole('tab', { name: /Avisos/ }).click();
  await expect(page.getByText('Aviso atualizado')).toBeVisible();
  await expect(page.getByText('Aviso antigo paginado')).toHaveCount(0);
  await page.getByRole('tab', { name: /Minha conta/ }).click();
  await page.getByLabel('Nome completo').fill('Nome atualizado');
  await page.getByRole('switch', { name: 'Receber e-mails dos casos' }).uncheck();
  await page.getByRole('button', { name: 'Salvar preferências' }).click();
  await expect(page.getByText('Preferências atualizadas.')).toBeVisible(); expect(saved).toBe(true);
  await page.getByRole('button', { name: 'Privacidade e exclusão de conta' }).click();
  await page.getByRole('button', { name: 'Excluir minha conta', exact: true }).click();
  await page.getByRole('button', { name: 'Confirmar solicitação de exclusão' }).click();
  await expect(page.getByText('Solicitação registrada. Acompanhe a resposta abaixo.')).toBeVisible(); expect(deleted).toBe(true);
});
