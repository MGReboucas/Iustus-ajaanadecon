import { expect, test, type Page } from '@playwright/test';

const id = '00000000-0000-0000-0000-000000000001';
const user = { id, name: 'Pessoa Teste', email: 'mobile@example.test', role: 'CLIENT', caseEmailEnabled: true };
const item = { id, version: 2, reference: '00000000', title: 'Revisão de cobrança', categoryLabel: 'Relações de consumo', state: 'EM_TRIAGEM', stateLabel: 'Em triagem', createdAt: '2026-10-06T12:00:00Z', description: 'Cobrança apresentada para análise do advogado.', occurredOn: '2026-10-01' };
const dashboard = { user, totalCases: 1, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [], membership: { active: true, expiresAt: '2027-10-06T12:00:00Z' }, submission: { canSubmit: true, mode: 'MEMBERSHIP', message: 'Associação ativa.' } };

async function mockApi(page: Page, options: { expired?: boolean; offline?: boolean } = {}) {
  let previousMessage: Record<string, unknown> | undefined;
  let firstSend = true;
  let proposal = { id, number: 1, scope: 'Defesa', feeCents: 120000, expenses: 'Custas separadas', paymentTerms: 'Conforme proposta', validUntil: '2099-01-01T00:00:00Z', status: 'OPEN', decidedAt: null as string | null };
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname.split('/mobile/')[1];
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization,content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers }); return; }
    if (path === 'auth/login') {
      if (request.postDataJSON().password === 'wrong') {
        await route.fulfill({ status: 403, headers, json: { error: { code: 'INVALID_CREDENTIALS', message: 'Não foi possível entrar com os dados informados.' } } }); return;
      }
      await route.fulfill({ headers, json: { token: 'x'.repeat(43), expiresAt: new Date(Date.now() + 86400000).toISOString(), user } }); return;
    }
    if (path === 'auth/recovery') { await route.fulfill({ status: 202, headers, json: { message: 'Se houver uma conta elegível, enviaremos as instruções por e-mail.' } }); return; }
    expect(request.headers()['authorization']).toBe('Bearer ' + 'x'.repeat(43));
    if (path === 'auth/logout') { await route.fulfill({ status: 204, headers }); return; }
    if (options.expired) { await route.fulfill({ status: 401, headers, json: { error: { code: 'AUTH_REQUIRED', message: 'Entre novamente.' } } }); return; }
    if (options.offline) { await route.abort(); return; }
    if (path.endsWith('/documents') || path.endsWith('/requests')) { await route.fulfill({ headers, json: { results: [], nextCursor: null } }); return; }
    if (path.endsWith('/workflow')) { await route.fulfill({ headers, json: { version: 2, state: item.state, scope: '', tasks: [] } }); return; }
    if (path.endsWith('/proposals')) { await route.fulfill({ headers, json: { results: [proposal], nextCursor: null } }); return; }
    if (path.endsWith('/decision')) {
      expect(request.postDataJSON()).toEqual({ version: 2, accepted: true });
      proposal = { ...proposal, status: 'ACCEPTED', decidedAt: new Date().toISOString() };
      await route.fulfill({ headers, json: { proposal, version: 3 } }); return;
    }
    if (path.endsWith('/messages')) {
      if (request.method() === 'POST') {
        const body = request.postDataJSON();
        if (previousMessage) expect(body.clientMessageId).toBe(previousMessage.clientMessageId);
        previousMessage = { ...body, id: 'sent-message', authorName: user.name, authorId: id, createdAt: item.createdAt };
        if (firstSend) { firstSend = false; await route.abort(); return; }
        await route.fulfill({ headers, json: previousMessage }); return;
      }
      await route.fulfill({ headers, json: { results: [], nextCursor: null } }); return;
    }
    const data = path === 'dashboard' ? dashboard : path === 'cases' ? { results: [item], nextCursor: null } : path.endsWith('/timeline') ? { results: [{ id, action: 'TRIAGE_STARTED', state: 'EM_TRIAGEM', reason: 'Documentação recebida.', createdAt: item.createdAt }], nextCursor: null } : item;
    await route.fulfill({ headers, json: data === item ? { ...item, canMessage: true } : data });
  });
}

async function signIn(page: Page, password = 'synthetic') {
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Entrar na minha conta' }).click();
}

test('login, dashboard, case history and logout', async ({ page }, testInfo) => {
  await mockApi(page);
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Entrar na minha conta' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('login.png'), fullPage: true, scale: 'css' });
  await signIn(page, 'wrong');
  await expect(page.getByRole('alert')).toContainText('Não foi possível entrar');
  await signIn(page);
  await expect(page.getByText('Olá, Pessoa.')).toBeVisible();
  await expect(page.getByText('Associação ativa', { exact: true })).toBeVisible();
  const tabLabel = await page.getByText('Minha conta', { exact: true }).boundingBox();
  expect(tabLabel).not.toBeNull();
  expect(tabLabel!.y + tabLabel!.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  await page.screenshot({ path: testInfo.outputPath('dashboard.png'), fullPage: true, scale: 'css' });
  await page.getByRole('button', { name: 'Ver todos os meus casos' }).click();
  await page.getByRole('button', { name: 'Abrir Revisão de cobrança: Em triagem' }).click();
  await expect(page.getByText(item.description)).toBeVisible();
  await expect(page.getByText('Documentação recebida.')).toBeVisible();
  await page.getByLabel('Sua mensagem', { exact: true }).fill('Tenho uma atualização sobre o caso.');
  await page.getByRole('button', { name: 'Enviar mensagem', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Não foi possível conectar');
  await expect(page.getByLabel('Sua mensagem', { exact: true })).toHaveValue('Tenho uma atualização sobre o caso.');
  await page.getByRole('button', { name: 'Enviar mensagem', exact: true }).click();
  await expect(page.getByLabel('Sua mensagem', { exact: true })).toHaveValue('');
  await expect(page.getByText('Tenho uma atualização sobre o caso.', { exact: true })).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Aceitar proposta 1', exact: true })).toBeDisabled();
  await page.getByRole('switch', { name: 'Confirmar leitura da proposta 1' }).check();
  await page.getByRole('button', { name: 'Aceitar proposta 1', exact: true }).click();
  await expect(page.getByText('Proposta 1 \u00b7 Aceita', { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('case.png'), fullPage: true, scale: 'css' });
  await page.goBack();
  await page.getByRole('tab', { name: /Minha conta/ }).click();
  await expect(page.getByText(user.email)).toBeVisible();
  await page.getByRole('button', { name: 'Sair da minha conta' }).click();
  await expect(page.getByRole('button', { name: 'Entrar na minha conta' })).toBeVisible();
  await page.goto('/case/' + id);
  await expect(page.getByRole('button', { name: 'Entrar na minha conta' })).toBeVisible();
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
});

test('recovery and expired sessions', async ({ page }) => {
  await mockApi(page, { expired: true });
  await page.goto('/');
  await page.getByRole('button', { name: 'Esqueci minha senha' }).click();
  await page.getByLabel('E-mail da sua conta').fill(user.email);
  await page.getByRole('button', { name: 'Enviar instruções' }).click();
  await expect(page.getByText('Se houver uma conta elegível, enviaremos as instruções por e-mail.')).toBeVisible();
  await page.getByRole('button', { name: 'Voltar para entrar' }).click();
  await signIn(page);
  await expect(page.getByRole('button', { name: 'Entrar na minha conta' })).toBeVisible();
});

test('offline dashboard can retry without losing the session', async ({ page }) => {
  const options = { offline: true };
  await mockApi(page, options);
  await page.goto('/'); await signIn(page);
  await expect(page.getByRole('alert')).toContainText('Não foi possível conectar');
  options.offline = false;
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(page.getByText('Olá, Pessoa.')).toBeVisible();
});

test('case deep link retains its destination through login', async ({ page }) => {
  await mockApi(page);
  await page.goto('/open-case/' + id);
  await signIn(page);
  await expect(page.getByText(item.description)).toBeVisible();
  await expect(page).toHaveURL(new RegExp('/case/' + id + '$'));
});

test('first access registers and confirms an email link inside the app', async ({ page }) => {
  let registered = false;
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', async route => {
    const req = route.request(); const path = new URL(req.url()).pathname.split('/mobile/')[1];
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (path === 'auth/context') return route.fulfill({ headers, json: { policyVersion: 'synthetic-v1', registrationAvailable: true, billingAvailable: false, checkoutAvailable: false } });
    if (path === 'auth/register') {
      expect(req.postDataJSON()).toEqual({ name: 'Novo associado', email: 'new@example.test', password: 'Synthetic-938!', policyVersion: 'synthetic-v1' });
      registered = true; return route.fulfill({ headers, status: 202, json: { message: 'Confirme o cadastro pelo e-mail.' } });
    }
    if (path === 'auth/verify') {
      expect(registered).toBe(true); expect(req.postDataJSON()).toEqual({ token: 'a'.repeat(43) });
      return route.fulfill({ headers, status: 204 });
    }
    throw new Error('Unexpected public route ' + path);
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Primeiro acesso', exact: true }).click();
  await page.getByLabel('Nome completo').fill('Novo associado');
  await page.getByLabel('E-mail de cadastro').fill('new@example.test');
  await page.getByLabel('Criar senha').fill('Synthetic-938!');
  await expect(page.getByRole('button', { name: 'Criar minha conta' })).toBeDisabled();
  await page.getByRole('switch', { name: 'Aceitar termos e privacidade' }).check();
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByText('Confirme o cadastro pelo e-mail.')).toBeVisible();
  await page.getByRole('button', { name: 'Já tenho o link do e-mail' }).click();
  await page.getByLabel('Link recebido por e-mail').fill('https://mobile-api.example.test/acessar#verify=' + 'a'.repeat(43));
  await page.getByRole('button', { name: 'Confirmar acesso' }).click();
  await expect(page.getByText('Acesso atualizado. Entre com seu e-mail e senha.')).toBeVisible();
});
