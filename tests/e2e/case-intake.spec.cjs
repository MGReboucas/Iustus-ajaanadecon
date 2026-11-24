const { test, expect } = require('../../frontend/node_modules/@playwright/test');

test('dez anexos ficam na mesma caixa e a remoção preserva os demais', async ({ page }) => {
  const id = '00000000-0000-0000-0000-000000000004';
  const item = { id, reference: 'ANEXOS', title: 'Teste de anexos', description: 'Relato fictício para testar vários anexos.', category: 'CIVIL', occurredOn: '2026-11-01', scopeAcknowledged: true, state: 'RASCUNHO', stateLabel: 'Rascunho', version: 1 };
  let versions = [];
  let count = 0;
  await page.route('**/api/v1/**', route => {
    const req = route.request();
    const path = new URL(req.url()).pathname.split('/api/v1/')[1];
    const send = json => route.fulfill({ json });
    if (path === 'auth/csrf') return send({ csrfToken: 'test' });
    if (path === 'dashboard/client') return send({ user: { id, name: 'Teste', role: 'CLIENT' } });
    if (path === 'dashboard/overview') return send({ totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [] });
    if (path === 'cases/catalog') return send({ categories: [{ id: 'CIVIL', label: 'Civil' }], states: [], intakeRequired: true, documentsAvailable: true, submission: { canSubmit: true } });
    if (path === 'cases') return send(req.method() === 'POST' ? item : { results: [], nextCursor: null });
    if (path === `cases/${id}`) return send(item);
    if (path === `cases/${id}/documents`) return send({ results: versions, nextCursor: null });
    if (path === `cases/${id}/documents/uploads`) {
      const uid = `00000000-0000-0000-0000-${String(++count).padStart(12, '0')}`;
      versions.push({ id: uid, documentId: uid, filename: req.postDataJSON().filename, number: 1, sizeBytes: 100, status: 'AVAILABLE', statusLabel: 'Disponível', uploadedById: id });
      return send({ uploadId: uid, uploadUrl: `/api/v1/uploads/${uid}/content`, directUpload: false });
    }
    if (path.startsWith('uploads/') && path.endsWith('/content')) return route.fulfill({ status: 204 });
    if (path.startsWith('uploads/') && path.endsWith('/complete')) return send({ status: 'QUARANTINED' });
    if (path.endsWith('/remove')) { versions = versions.filter(v => v.id !== path.split('/')[3]); return route.fulfill({ status: 204 }); }
    return send({ results: [], nextCursor: null });
  });
  await page.goto('/cliente#meus-casos');
  await page.getByRole('button', { name: 'Cadastrar ocorrência', exact: true }).click();
  await page.getByLabel('Arquivo para anexar').setInputFiles(Array.from({ length: 10 }, (_, i) => ({ name: `arquivo-${i + 1}.pdf`, mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n%%EOF') })));
  await expect(page.locator('.document-chips li')).toHaveCount(10);
  await expect(page.locator('.document-box')).toHaveCount(1);
  await expect(page.locator('.document-remove').last()).toBeEnabled();
  await page.locator('.document-box').screenshot({ path: '../.local/documents-e2e/anexos-compactos-desktop.png' });
  const box = await page.locator('.document-box').boundingBox();
  expect(box.height).toBeLessThan(350);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('.document-box').screenshot({ path: '../.local/documents-e2e/anexos-compactos-mobile.png' });
  const chip = page.locator('.document-chips li').first();
  const close = await chip.locator('.document-remove').boundingBox();
  const bounds = await chip.boundingBox();
  expect(close.x + close.width).toBeLessThanOrEqual(bounds.x + bounds.width);
  await page.getByRole('button', { name: 'Remover arquivo-1.pdf (v1)', exact: true }).click();
  await expect(page.locator('.document-chips li')).toHaveCount(9);
  await expect(page.getByRole('button', { name: 'Remover arquivo-10.pdf (v1)', exact: true })).toBeVisible();
});

test('cliente anexa automaticamente e remove cada arquivo pelo ícone', async ({ page }) => {
  const id = '00000000-0000-0000-0000-000000000003';
  let removed = false;
  let removalAttempts = 0;
  let uploadCount = 0;
  let filename = 'teste.pdf';
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
    if (path === `cases/${id}/documents`) return send({ results: removed ? [] : [{ id, documentId: id, filename, number: 1, sizeBytes: 100, status: 'AVAILABLE', statusLabel: 'Disponível', uploadedById: id }], nextCursor: null });
    if (path === `cases/${id}/documents/uploads`) {
      filename = req.postDataJSON().filename;
      uploadCount += 1;
      return send({ uploadId: id, uploadUrl: `/api/v1/uploads/${id}/content`, directUpload: false });
    }
    if (path === `uploads/${id}/content`) return route.fulfill({ status: 204 });
    if (path === `uploads/${id}/complete`) { removed = false; return send({ status: 'QUARANTINED' }); }
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
  const uploaded = page.getByRole('button', { name: 'Remover selecionado.pdf (v1)', exact: true });
  await expect(uploaded).toBeVisible();
  await expect(page.getByRole('button', { name: 'Enviar arquivo', exact: true })).toHaveCount(0);
  expect(uploadCount).toBe(1);
  await uploaded.click();
  await expect(page.getByText('Nenhum documento enviado neste caso.')).toBeVisible();
  // Choosing the same file again must fire a fresh upload, not keep a stale selection.
  await page.getByLabel('Arquivo para anexar').setInputFiles({ name: 'selecionado.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n%%EOF') });
  await expect(uploaded).toBeVisible();
  expect(uploadCount).toBe(2);
  await uploaded.click();
  await expect(page.getByText('Nenhum documento enviado neste caso.')).toBeVisible();
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
  await expect(page.getByRole('heading', { name: 'Documentos que comprovam a ocorrência' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Salvar rascunho' })).toHaveCount(0);
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

test('autosave preserva edicoes durante resposta lenta e permite tentar novamente', async ({ page }) => {
  const id = '00000000-0000-0000-0000-000000000009';
  let item = { id, reference: 'AUTO', title: '', description: '', category: '', state: 'RASCUNHO', stateLabel: 'Rascunho', version: 1 };
  let patches = 0, fail = false;
  await page.route('**/api/v1/**', async route => {
    const req = route.request(), path = new URL(req.url()).pathname.split('/api/v1/')[1];
    const send = json => route.fulfill({ json });
    if (path === 'auth/csrf') return send({ csrfToken: 'test' });
    if (path === 'dashboard/client') return send({ user: { id, name: 'Teste', role: 'CLIENT' } });
    if (path === 'dashboard/overview') return send({ totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [] });
    if (path === 'cases/catalog') return send({ categories: [], states: [], documentsAvailable: true, submission: { canSubmit: true } });
    if (path === 'cases') return send(req.method() === 'POST' ? item : { results: [item], nextCursor: null });
    if (path === `cases/${id}`) {
      if (req.method() === 'PATCH') {
        patches++;
        if (fail) return route.fulfill({ status: 503, json: { error: { code: 'UNAVAILABLE', message: 'Falha temporaria' } } });
        await new Promise(resolve => setTimeout(resolve, 900));
        item = { ...item, ...req.postDataJSON(), version: item.version + 1 };
      }
      return send(item);
    }
    return send({ results: [], nextCursor: null });
  });
  await page.goto('/cliente#meus-casos');
  await page.getByRole('button', { name: /Cadastrar ocorr/, exact: false }).click();
  const title = page.locator('#case-intake input').first();
  await title.fill('Primeira versao');
  await expect.poll(() => patches).toBe(1);
  await title.fill('Ultima versao');
  await expect(page.getByText('Rascunho salvo', { exact: true })).toBeVisible();
  expect(item.title).toBe('Ultima versao');
  await expect(title).toHaveValue('Ultima versao');
  fail = true;
  await title.fill('Preservar em falha');
  await expect(page.getByRole('button', { name: 'Tentar novamente' })).toBeVisible();
  await expect(title).toHaveValue('Preservar em falha');
  fail = false;
  await page.getByRole('button', { name: 'Tentar novamente' }).click();
  await expect(page.getByText('Rascunho salvo', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Voltar aos meus casos' }).click();
  await page.getByRole('button', { name: /Preservar em falha/ }).click();
  await expect(title).toHaveValue('Preservar em falha');
});
