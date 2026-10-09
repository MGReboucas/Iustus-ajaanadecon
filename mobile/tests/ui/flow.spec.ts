import { test, expect } from '@playwright/test';

const id = '00000000-0000-0000-0000-000000000101';
const documentId = '00000000-0000-0000-0000-000000000102';
const versionId = '00000000-0000-0000-0000-000000000103';
const user = { id, name: 'Associado Teste', email: 'flow@example.test', role: 'CLIENT', caseEmailEnabled: true };

test('create, edit, upload, submit, complement, mandate, published work and privacy', async ({ page }, info) => {
  let item = { id, title: '', description: '', category: '', categoryLabel: 'Consumo', scopeAcknowledged: false, occurredOn: '', version: 1, state: 'RASCUNHO', stateLabel: 'Rascunho', reference: '00000101', createdAt: '2026-01-01T12:00:00Z' };
  let uploaded = false; let responded = false; let signed = false; let privacy = false;
  const document = { id: versionId, documentId, uploadedById: id, number: 1, filename: 'prova.pdf', sizeBytes: 30, status: 'AVAILABLE', statusLabel: 'Verificado', createdAt: item.createdAt };
  const failures: string[] = [];
  page.on('pageerror', error => failures.push(error.message));
  await page.route('https://mobile-api.example.test/api/v1/mobile/**', async route => {
    const req = route.request(); const path = new URL(req.url()).pathname.split('/mobile/')[1];
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization,content-type,idempotency-key', 'access-control-allow-methods': 'GET,POST,PATCH,OPTIONS' };
    const reply = (json: unknown, status = 200) => route.fulfill({ headers, status, json });
    if (req.method() === 'OPTIONS') return route.fulfill({ headers, status: 204 });
    if (path === 'auth/login') return reply({ token: 'x'.repeat(43), expiresAt: new Date(Date.now() + 86400000).toISOString(), user });
    expect(req.headers().authorization).toBe('Bearer ' + 'x'.repeat(43));
    if (path === 'dashboard') return reply({ user, totalCases: 1, attentionCount: 1, unreadCount: 1, states: [], attentionCases: [], recentActivity: [], membership: { active: true, expiresAt: '2027-01-01' }, submission: { canSubmit: true, message: 'Atendimento liberado.' } });
    if (path === 'cases/catalog') return reply({ categories: [{ id: 'CONSUMER', label: 'Consumo' }], documentsAvailable: true, intakeRequired: true, submission: { canSubmit: true, message: 'Atendimento liberado.' } });
    if (path === 'cases' && req.method() === 'POST') { item = { ...item, ...req.postDataJSON() }; return reply(item, 201); }
    if (path === `cases/${id}` && req.method() === 'PATCH') { expect(req.postDataJSON().version).toBe(item.version); item = { ...item, ...req.postDataJSON(), version: item.version + 1 }; return reply(item); }
    if (path === `cases/${id}`) return reply(item);
    if (path.endsWith('/documents/uploads')) { expect(req.postDataJSON().mime).toBe('application/pdf'); return reply({ uploadId: versionId, version: document, directUpload: false }, 201); }
    if (path === `uploads/${versionId}/content`) { expect(req.headers()['content-type']).toBe('application/octet-stream'); return route.fulfill({ headers, status: 204 }); }
    if (path.endsWith('/complete')) { expect(req.postDataJSON().checksum).toMatch(/^[0-9a-f]{64}$/); uploaded = true; item.version++; return reply(document, 202); }
    if (path.endsWith('/documents')) return reply({ results: uploaded ? [document] : [], nextCursor: null });
    if (path.endsWith('/submit')) {
      expect(uploaded).toBe(true); expect(req.headers()['idempotency-key']).toBeTruthy(); expect(req.postDataJSON().version).toBe(item.version);
      item = { ...item, version: item.version + 1, state: 'AGUARDANDO_CLIENTE', stateLabel: 'Aguardando cliente' }; return reply(item);
    }
    if (path.endsWith('/requests')) return reply({ results: [{ id, description: 'Confirme o ocorrido', responded, resolved: false, response: responded ? 'Complemento sintético enviado.' : '', resolution: '', attachments: [] }], nextCursor: null });
    if (path.endsWith('/response')) {
      expect(req.postDataJSON().documentVersionIds).toEqual([versionId]); responded = true;
      item = { ...item, version: item.version + 1, state: 'AGUARDANDO_PROCURACAO', stateLabel: 'Aguardando procuração' }; return reply(item);
    }
    if (path.endsWith('/workflow')) {
      if (req.method() === 'POST') { expect(req.postDataJSON().action).toBe('SIGN'); expect(req.postDataJSON().documentId).toBe(versionId); signed = true; item.version++; item.state = 'EM_ACOMPANHAMENTO'; item.stateLabel = 'Em acompanhamento'; }
      return reply({ version: item.version, scope: responded ? 'Defesa contratada' : '', state: item.state, mandate: document, signedMandate: signed ? document : null, publishedText: signed ? 'Peça revisada disponibilizada ao associado.' : '', receipt: signed ? document : null, protocol: signed ? 'PROTOCOLO-TESTE' : '', tasks: signed ? [{ id, kind: 'HEARING', title: 'Audiência sintética', dueAt: '2026-12-01T12:00:00Z', completedAt: null, outcome: '' }] : [] });
    }
    if (path === 'privacy/requests') {
      if (req.method() === 'POST') { expect(req.postDataJSON().kind).toBe('DELETION'); privacy = true; return reply({ id, status: 'OPEN' }, 201); }
      return reply({ results: privacy ? [{ id, kind: 'DELETION', description: 'Solicito excluir minha conta de teste.', status: 'OPEN', response: '' }] : [], nextCursor: null });
    }
    if (path.endsWith('/proposals') || path.endsWith('/messages') || path.endsWith('/timeline')) return reply({ results: [], nextCursor: null });
    throw new Error(`Unexpected endpoint: ${req.method()} ${path}`);
  });
  await page.goto('/');
  await page.getByLabel('E-mail', { exact: true }).fill(user.email); await page.getByLabel('Senha', { exact: true }).fill('synthetic');
  await page.getByRole('button', { name: 'Entrar na minha conta' }).click();
  await page.getByRole('button', { name: 'Nova ocorrência' }).click();
  await page.getByLabel('Título da ocorrência').fill('Ocorrência pelo celular');
  await page.getByRole('button', { name: 'Consumo', exact: true }).click();
  await page.getByLabel('Data do ocorrido (AAAA-MM-DD)').fill('2026-01-01');
  await page.getByLabel('Relato do ocorrido').fill('Relato sintético com detalhes suficientes para análise.');
  await page.getByRole('switch', { name: 'Ciência do escopo do atendimento' }).check();
  await page.getByRole('button', { name: 'Salvar ocorrência e anexar documentos' }).click();
  await page.getByLabel('Título da ocorrência').fill('Ocorrência revisada');
  await expect(page.getByRole('button', { name: 'Enviar ocorrência para triagem' })).toBeDisabled();
  await page.getByRole('button', { name: 'Salvar alterações' }).click();
  await expect(page.getByRole('button', { name: 'Enviar ocorrência para triagem' })).toBeEnabled();
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: 'Anexar arquivo', exact: true }).click();
  await (await chooser).setFiles('tests/fixtures/prova.pdf');
  await expect(page.getByText('Arquivo recebido.', { exact: false })).toBeVisible();
  await expect(page.getByText('Verificado', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Enviar ocorrência para triagem' }).click();
  await expect(page.getByText('Confirme o ocorrido', { exact: true })).toBeVisible();
  await page.getByRole('switch', { name: 'Selecionar prova.pdf versão 1' }).check();
  await page.getByLabel('Resposta ao complemento').fill('Complemento sintético enviado.');
  await page.getByRole('button', { name: 'Enviar complemento' }).click();
  await expect(page.getByRole('button', { name: 'Entregar procuração assinada' })).toBeVisible();
  await page.getByRole('switch', { name: 'Selecionar prova.pdf versão 1' }).check();
  await page.getByRole('button', { name: 'Entregar procuração assinada' }).click();
  await expect(page.getByText('Peça revisada disponibilizada ao associado.')).toBeVisible();
  await expect(page.getByText('Audiência sintética', { exact: true })).toBeVisible();
  await page.screenshot({ path: info.outputPath('complete-case.png'), fullPage: true });
  // Navigate through the existing stack without reloading the memory-only web session.
  await page.goBack();
  await page.getByRole('tab', { name: /Minha conta/ }).click();
  await page.getByRole('button', { name: 'Privacidade e exclusão de conta' }).click();
  await page.getByRole('button', { name: 'Excluir minha conta', exact: true }).click();
  await page.getByLabel('Descreva sua solicitação').fill('Solicito excluir minha conta de teste.');
  await page.getByRole('button', { name: 'Confirmar solicitação de exclusão' }).click();
  await expect(page.getByText('Solicitação registrada.', { exact: false })).toBeVisible();
  expect(failures).toEqual([]);
});
