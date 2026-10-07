const { test, expect } = require('../../frontend/node_modules/@playwright/test');
const id = '00000000-0000-0000-0000-000000000001';
async function setup(page, role) {
  let version = 1;
  let proposals = role === 'CLIENT' ? [{ id, number: 1, scope: 'Defesa do caso', feeCents: 150000, expenses: 'Custas separadas', paymentTerms: 'Pagamento externo', validUntil: '2099-01-01T00:00:00Z', status: 'OPEN', decidedAt: null }] : [];
  const writes = [];
  const item = () => ({ id, reference: 'CASO-TESTE', title: 'Caso de teste', description: 'Relato de teste', category: 'TRAFFIC', categoryLabel: 'Multas', state: 'EM_TRIAGEM', stateLabel: 'Em triagem', version, lawyerId: id });
  await page.route('**/api/v1/**', route => {
    const req = route.request();
    const endpoint = new URL(req.url()).pathname.split('/api/v1/')[1];
    const send = json => route.fulfill({ json });
    if (endpoint === 'auth/csrf') return send({ csrfToken: 'test' });
    if (/^dashboard\/(client|team)$/.test(endpoint)) return send({ user: { id, name: 'Teste', email: 'test@example.test', role, caseEmailEnabled: true } });
    if (endpoint === 'dashboard/overview') return send({ totalCases: 1, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [], submission: null });
    if (endpoint === 'cases/catalog') return send({ categories: [], states: [], documentsAvailable: false, submission: { canSubmit: false, message: '' } });
    if (endpoint === 'cases') return send({ results: [item()], nextCursor: null });
    if (endpoint === `cases/${id}`) return send(item());
    if (endpoint === `cases/${id}/proposals` && req.method() === 'POST') {
      const body = req.postDataJSON(); writes.push(body); version++;
      proposals = [{ ...body, id, number: 1, status: 'OPEN', decidedAt: null }];
      return send({ proposal: proposals[0], version });
    }
    if (endpoint === `cases/${id}/proposals/${id}/decision`) {
      const body = req.postDataJSON(); writes.push(body); version++;
      proposals[0].status = body.accepted ? 'ACCEPTED' : 'DECLINED';
      proposals[0].decidedAt = new Date().toISOString();
      return send({ proposal: proposals[0], version });
    }
    if (endpoint === `cases/${id}/proposals`) return send({ results: proposals, nextCursor: null });
    return send({ results: [], nextCursor: null });
  });
  await page.goto(role === 'CLIENT' ? '/cliente' : '/advogado');
  await page.getByRole('button', { name: /CASO-TESTE/ }).click();
  await expect(page.getByRole('region', { name: 'Propostas de atendimento' })).toBeVisible();
  return writes;
}

test('cliente revisa termos antes de aceitar', async ({ page }) => {
  const writes = await setup(page, 'CLIENT');
  const region = page.getByRole('region', { name: 'Propostas de atendimento' });
  await expect(region.getByRole('button', { name: 'Aceitar proposta 1' })).toBeDisabled();
  await region.getByRole('checkbox').check();
  await region.getByRole('button', { name: 'Aceitar proposta 1' }).click();
  await expect(region.getByRole('heading', { name: 'Proposta 1 · Aceita' })).toBeVisible();
  expect(writes).toEqual([{ version: 1, accepted: true }]);
});

test('advogado publica honorários em centavos e mantém termos visíveis', async ({ page }) => {
  const writes = await setup(page, 'LAWYER');
  const region = page.getByRole('region', { name: 'Propostas de atendimento' });
  await region.getByLabel('Escopo do atendimento').fill('Defesa do caso');
  await region.getByLabel('Honorários em reais').fill('1500,99');
  await region.getByLabel('Custas e outras despesas').fill('Custas separadas');
  await region.getByLabel('Condições de pagamento').fill('Pagamento externo');
  await region.getByLabel('Validade da proposta').fill('2099-01-01T12:00');
  await region.getByRole('button', { name: 'Apresentar proposta ao cliente' }).click();
  await expect(region.getByRole('heading', { name: 'Proposta 1 · Aguardando decisão' })).toBeVisible();
  expect(writes[0].feeCents).toBe(150099);
  expect(writes[0].scope).toBe('Defesa do caso');
});
