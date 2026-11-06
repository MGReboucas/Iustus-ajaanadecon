const { test, expect } = require('../../frontend/node_modules/@playwright/test');

test('admin filters people, confirms revocation and restores access', async ({ page }) => {
  const writes = [];
  const people = [
    { id: 'admin', name: 'Administrador', email: 'admin@example.test', role: 'ADMIN', active: true, activated: true, version: 1 },
    { id: 'lawyer', name: 'Advogada Teste', email: 'lawyer@example.test', role: 'LAWYER', active: true, activated: true, version: 1 },
    { id: 'client', name: 'Cliente Teste', email: 'client@example.test', role: 'CLIENT', active: true, activated: true, version: 1 },
  ];
  await page.route('**/api/v1/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    let body = { results: [], nextCursor: null };
    if (path.endsWith('/auth/csrf')) body = { csrfToken: 'test' };
    if (path.endsWith('/admin/invitations')) body = { message: 'Se o endereço for elegível, o convite será enviado.' };
    if (path.endsWith('/dashboard/team')) body = { user: people[0] };
    if (path.endsWith('/dashboard/overview')) body = { totalCases: 0, attentionCount: 0, unreadCount: 0, states: [], attentionCases: [], recentActivity: [] };
    if (path.endsWith('/cases/catalog')) body = { categories: [], states: [], documentsAvailable: false };
    if (path.endsWith('/details')) body = { user: people.find(p => p.id === path.split('/').at(-2)), joinedAt: '2026-01-01T12:00:00Z', membership: { status: 'ACTIVE', environment: 'production', startsAt: '2026-01-01T12:00:00Z', expiresAt: '2027-01-01T12:00:00Z' }, results: [{ id: 'audit', createdAt: '2026-02-01T12:00:00Z', active: true, actor: 'admin@example.test', reason: 'Acesso revisado pela administração' }], nextCursor: null };
    if (path.endsWith('/admin/users')) {
      const role = url.searchParams.get('role'), status = url.searchParams.get('status'), search = url.searchParams.get('search') || '';
      const results = people.filter(p => (!role || p.role === role) && (!status || (status === 'active' ? p.active && p.activated : status === 'revoked' ? !p.active : p.active && !p.activated)) && `${p.name} ${p.email}`.toLowerCase().includes(search.toLowerCase()));
      body = { results, total: results.length, nextCursor: null, summary: { total: 3, lawyers: people.filter(p => p.role === 'LAWYER' && p.active).length, clients: people.filter(p => p.role === 'CLIENT' && p.active).length, pending: 0, revoked: people.filter(p => !p.active).length } };
    }
    if (path.endsWith('/access')) { const payload = req.postDataJSON(); writes.push(payload); const person = people.find(p => path.split('/').at(-2) === p.id); person.active = payload.active; person.version++; body = person; }
    await route.fulfill({ json: body });
  });
  await page.goto('/advogado');
  await expect(page.getByRole('heading', { name: 'Pessoas e acessos' })).toBeVisible();
  await page.getByRole('button', { name: /Aprovar profissional/ }).click();
  await page.getByLabel('E-mail do profissional').fill('new-lawyer@example.test');
  await page.getByRole('button', { name: 'Aprovar e enviar ativação' }).click();
  await expect(page.getByRole('status', { name: 'Resultado da gestão de usuários' })).toContainText('convite');
  await expect(page.getByRole('row').filter({ hasText: 'admin@example.test' }).getByRole('button', { name: /Revogar|Aprovar/ })).toHaveCount(0);
  await page.getByRole('button', { name: /Clientes ativos/ }).click();
  await expect(page.getByRole('row').filter({ hasText: 'client@example.test' })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: 'lawyer@example.test' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Detalhes', exact: true }).click();
  await expect(page.getByRole('dialog').getByText('Associação vigente', { exact: true })).toBeVisible();
  await expect(page.getByRole('dialog').getByText('Acesso revisado pela administração')).toBeVisible();
  await page.getByRole('button', { name: 'Fechar', exact: true }).click();
  await page.getByRole('button', { name: 'Revogar acesso', exact: true }).click();
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  expect(writes).toHaveLength(0);
  await page.getByRole('button', { name: 'Revogar acesso', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Confirmar alteração de acesso' })).toBeDisabled();
  await page.getByLabel('Motivo da alteração').fill('Solicitação de revisão de acesso');
  await page.getByRole('button', { name: 'Confirmar alteração de acesso' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByText('Nenhuma pessoa encontrada')).toBeVisible();
  await page.getByRole('button', { name: /Acessos revogados/ }).click();
  await page.getByRole('button', { name: 'Aprovar acesso', exact: true }).click();
  await page.getByLabel('Motivo da alteração').fill('Revisão concluída pelo administrador');
  await page.getByRole('button', { name: 'Confirmar alteração de acesso' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  expect(writes.map(w => [w.active, w.version])).toEqual([[false, 1], [true, 2]]);
  await page.getByRole('button', { name: 'Limpar filtros' }).click();
  await page.getByLabel('Buscar nome ou e-mail').fill('lawyer@');
  await page.getByRole('button', { name: 'Buscar', exact: true }).click();
  await expect(page.getByRole('row').filter({ hasText: 'lawyer@example.test' })).toBeVisible();
  await expect(page.getByRole('row').filter({ hasText: 'client@example.test' })).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
