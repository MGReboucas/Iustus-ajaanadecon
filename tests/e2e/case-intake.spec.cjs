const { test, expect } = require('../../frontend/node_modules/@playwright/test');

test('cliente remove anexo do rascunho e limpa seleção antes do upload', async ({ page }) => {
  const id = '00000000-0000-0000-0000-000000000003';
  let removed = false;
  let removalAttempts = 0;
  const item = { id, reference: 'RASCUNHO', title: 'Teste', description: 'Relato fictício para testar anexos.', category: 'CIVIL', occurredOn: '2026-11-01', scopeAcknowledged: true, state: 'RASCUNHO', stateLabel: 'Rascunho', version: 1 };
  await page.route('**/api/v1/**', route => {
    const req = route.request();
    const path = new URL(req.url()).pathname.split('/api/v1/')[1];
    const send = json => route.fulfill({ json });
    if (path === 'auth/csrf') return send({ csrfToken: 'test' });
    if (path === 'dashboard/client') return send({ user: { id, name: 'Teste', role: 'CLIENT' } });
    if (path === 'dashboard/overview') return send({ totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [] });
    if (path === 'cases/catalog') return send({ categories: [{ id: 'CIVIL', label: 'Civil' }], states: [], intakeRequired: true, documentsAvailable: true, submission: { canSubmit: true } });
    if (path === 'cases') return send(req.method() === 'POST' ? item : { results: [], nextCursor: null });
    if (path === `cases/${id}`) return send({ ...item, version: removed ? 2 : 1 });
    if (path === `cases/${id}/documents`) return send({ results: removed ? [] : [{ id, documentId: id, filename: 'teste.pdf', number: 1, sizeBytes: 100, status: 'AVAILABLE', statusLabel: 'Disponível', uploadedById: id }], nextCursor: null });
    if (path === `documents/${id}/versions/${id}/remove`) {
      removalAttempts += 1;
      if (removalAttempts === 1) return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Recurso não encontrado.' } } });
      expect(req.method()).toBe('POST');
      expect(req.headers()['x-csrftoken']).toBe('test');
      removed = true;
      return route.fulfill({ status: 204 });
    }
    return send({ results: [], nextCursor: null });
  });
  await page.goto('/cliente#meus-casos');
  await page.getByRole('button', { name: 'Cadastrar ocorrência', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Enviar ocorrência para análise' })).toBeEnabled();
  const remove = page.getByRole('button', { name: 'Remover teste.pdf (v1)', exact: true });
  await expect(remove).toHaveText('×');
  await expect(remove).toHaveCSS('width', '32px');
  await expect(remove).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await page.screenshot({ path: '../.local/documents-e2e/remover-anexo-desktop.png', fullPage: true });
  await remove.click();
  await expect(page.getByText('Recurso não encontrado.', { exact: false })).toBeVisible();
  await expect(remove).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await remove.scrollIntoViewIfNeeded();
  await page.screenshot({ path: '../.local/documents-e2e/remover-anexo-mobile.png' });
  await remove.click();
  await expect(page.getByText('Nenhum documento enviado neste caso.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Enviar ocorrência para análise' })).toBeDisabled();
  await page.getByLabel('Arquivo para anexar').setInputFiles({ name: 'selecionado.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n%%EOF') });
  await page.getByRole('button', { name: 'Limpar seleção' }).click();
  await expect(page.getByRole('button', { name: 'Enviar arquivo', exact: true })).toBeDisabled();
  expect(removed).toBe(true);
});

test('cadastro reúne anexos, salva antes de enviar e mostra análise sem blocos vazios', async ({ page }) => {
  const id = '00000000-0000-0000-0000-000000000001';
  let item = { id, reference: 'OCORRENCIA', title: '', description: '', category: '', state: 'RASCUNHO', stateLabel: 'Rascunho', version: 1 };
  const writes = [];
  await page.route('**/api/v1/**', route => {
    const req = route.request();
    const path = new URL(req.url()).pathname.split('/api/v1/')[1];
    const send = json => route.fulfill({ json });
    if (path === 'auth/csrf') return send({ csrfToken: 'test' });
    if (path === 'dashboard/client') return send({ user: { id, name: 'Teste', role: 'CLIENT' } });
    if (path === 'dashboard/overview') return send({ totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [] });
    if (path === 'cases/catalog') return send({ categories: [{ id: 'CIVIL', label: 'Civil' }], states: [], intakeRequired: true, documentsAvailable: true, submission: { canSubmit: true } });
    if (path === 'cases') return send(req.method() === 'POST' ? item : { results: [], nextCursor: null });
    if (path === `cases/${id}`) {
      if (req.method() === 'PATCH') { writes.push('save'); item = { ...item, ...req.postDataJSON(), version: 2 }; }
      return send(item);
    }
    if (path === `cases/${id}/submit`) {
      writes.push('submit'); expect(req.postDataJSON().version).toBe(2);
      item = { ...item, state: 'SUBMETIDO', stateLabel: 'Enviado para distribuição', version: 3 }; return send(item);
    }
    if (path === `cases/${id}/documents`) return send({ results: [{ id, documentId: id, filename: 'comprovante.pdf', number: 1, sizeBytes: 100, status: 'AVAILABLE', statusLabel: 'Disponível', uploadedById: id }], nextCursor: null });
    return send({ results: [], nextCursor: null });
  });
  await page.goto('/cliente#meus-casos');
  await page.getByRole('button', { name: 'Cadastrar ocorrência', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Documentos comprobatórios' })).toBeVisible();
  for (const name of ['Propostas de atendimento', 'Conversa do caso', 'Documentos do caso', 'Histórico']) await expect(page.getByRole('heading', { name, exact: true })).toHaveCount(0);
  await page.getByLabel('Título do caso').fill('Problema com viagem');
  await page.getByLabel('Categoria', { exact: true }).selectOption('CIVIL');
  await page.getByLabel('Data do ocorrido').fill('2026-11-01');
  await page.getByLabel('Descrição do que aconteceu').fill('Meu voo foi cancelado e preciso de atendimento.');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Enviar ocorrência para análise' }).click();
  await expect(page.locator('.case-detail .case-badge').first()).toHaveText('Em análise');
  expect(writes).toEqual(['save', 'submit']);
  await expect(page.getByRole('heading', { name: 'Propostas de atendimento' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Documentos do caso' })).not.toBeVisible();
});

test('verificação atualiza anexos e versão do caso antes de permitir o envio', async ({ page }) => {
  const id = '00000000-0000-0000-0000-000000000002';
  let reads = 0;
  let submitted = false;
  let item = { id, reference: 'ANEXO', title: 'Caso com documento', description: 'Relato da ocorrência para análise.', category: 'CIVIL', occurredOn: '2026-11-01', scopeAcknowledged: true, state: 'RASCUNHO', stateLabel: 'Rascunho', version: 1 };
  await page.route('**/api/v1/**', async route => {
    const req = route.request();
    const path = new URL(req.url()).pathname.split('/api/v1/')[1];
    const send = json => route.fulfill({ json });
    if (path === 'auth/csrf') return send({ csrfToken: 'test' });
    if (path === 'dashboard/client') return send({ user: { id, name: 'Teste', role: 'CLIENT' } });
    if (path === 'dashboard/overview') return send({ totalCases: 1, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [] });
    if (path === 'cases/catalog') return send({ categories: [{ id: 'CIVIL', label: 'Civil' }], states: [], intakeRequired: true, documentsAvailable: true, submission: { canSubmit: true } });
    if (path === 'cases') return send(req.method() === 'POST' ? item : { results: [], nextCursor: null });
    if (path === `cases/${id}`) return send(item);
    if (path === `cases/${id}/documents`) {
      reads += 1;
      if (reads >= 2) {
        // Reconciliation finishes after the request starts, exposing parallel-read races.
        await new Promise(resolve => setTimeout(resolve, 150));
        item = { ...item, version: 2 };
      }
      return send({ results: [{ id, documentId: id, filename: 'prova.pdf', number: 1, sizeBytes: 100,
        status: reads >= 2 ? 'AVAILABLE' : 'QUARANTINED', statusLabel: reads >= 2 ? 'Disponível' : 'Aguardando verificação', uploadedById: id }], nextCursor: null });
    }
    if (path === `cases/${id}/submit`) {
      expect(req.postDataJSON().version).toBe(2);
      submitted = true;
      item = { ...item, state: 'SUBMETIDO', stateLabel: 'Enviado', version: 3 };
      return send(item);
    }
    return send({ results: [], nextCursor: null });
  });
  await page.goto('/cliente#meus-casos');
  await page.getByRole('button', { name: 'Cadastrar ocorrência', exact: true }).click();
  const sendCase = page.getByRole('button', { name: 'Enviar ocorrência para análise' });
  await expect(sendCase).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Baixar prova.pdf (v1)', exact: true })).toBeDisabled();
  await expect(sendCase).toBeEnabled({ timeout: 25000 });
  await expect(page.getByRole('button', { name: 'Baixar prova.pdf (v1)', exact: true })).toBeEnabled();
  await sendCase.click();
  await expect(page.locator('.case-detail .case-badge').first()).toHaveText('Em análise');
  expect(submitted).toBe(true);
});
