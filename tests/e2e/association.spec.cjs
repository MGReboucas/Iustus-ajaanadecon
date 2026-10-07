const { test, expect } = require('../../frontend/node_modules/@playwright/test');
const { execFileSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const python = path.join(root, 'backend/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const origin = 'http://localhost:3011';
const password = 'Synthetic-Browser-Passphrase-938!';
function fixture(action, email) { return JSON.parse(execFileSync(python, [path.join(__dirname, 'fixture.py'), action, email], { encoding: 'utf8', windowsHide: true })); }
function address() { return `e2e-${randomUUID()}@example.test`; }
async function login(page, email) {
  await page.goto(origin + '/acessar');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Acessar plataforma', exact: true }).click();
}
const proof = { name: 'comprovante-sintetico.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF') };
async function upload(page, email, file = proof) {
  await page.getByLabel('Arquivo para anexar').setInputFiles(file);
  await page.getByRole('button', { name: 'Enviar arquivo', exact: true }).click();
  await expect(page.getByText('Arquivo recebido. Aguarde a verificação e atualize a lista.')).toBeVisible();
  fixture('document-scan-fixture', email);
  await page.getByRole('button', { name: 'Atualizar documentos', exact: true }).click();
  await expect(page.getByRole('button', { name: `Baixar ${file.name} (v1)`, exact: true })).toBeEnabled();
}

test('associado paga, ativa, envia ocorrência; advogado aprova e solicita procuração do caso', async ({ browser }) => {
  test.skip(process.env.IUSTUS_E2E_ASSOCIATION !== 'true', 'Requer o perfil de associação');
  const customer = address(), lawyer = address();
  fixture('lawyer', lawyer); fixture('paid-member', customer);
  const c = await browser.newContext(), l = await browser.newContext();
  const cp = await c.newPage(), lp = await l.newPage();
  await cp.goto(origin + '/acessar');
  await expect(cp.getByRole('button', { name: 'Criar conta de cliente' })).toHaveCount(0);
  await cp.goto(fixture('mail', customer).body.match(/http[^\s]+/)[0]);
  await cp.getByLabel('Nome completo').fill('Associado Jornada');
  await cp.getByLabel('Senha', { exact: true }).fill(password);
  await cp.getByRole('button', { name: 'Concluir cadastro de associado' }).click();
  await expect(cp.locator('.auth-message')).toContainText('Cadastro concluído');
  await login(cp, customer); await expect(cp).toHaveURL(/\/cliente$/);
  await expect(cp.getByRole('heading', { name: 'Suas solicitações por situação' })).toBeVisible();
  await cp.getByRole('button', { name: 'Cadastrar ocorrência', exact: true }).click();
  const title = 'Ocorrência sintética ' + randomUUID().slice(0, 8);
  await cp.getByLabel('Título do caso').fill(title);
  await cp.getByLabel('Categoria', { exact: true }).selectOption('CONSUMER');
  await cp.getByLabel('Data do ocorrido').fill('2026-01-10');
  await cp.getByLabel('Descrição do que aconteceu').fill('Relato fictício detalhado para testar análise e procuração específica.');
  await cp.getByLabel(/Estou ciente/).check();
  await cp.getByRole('button', { name: 'Salvar rascunho', exact: true }).click();
  await expect(cp.getByText('Alteração registrada.', { exact: true })).toBeVisible();
  await upload(cp, customer);
  await cp.getByRole('button', { name: 'Enviar ocorrência para análise' }).click();
  await expect(cp.locator('.case-detail > .cases-heading')).toContainText('Enviado para distribuição');
  // Distribuição é automática. Encontrar o responsável real evita depender de outras fixtures.
  const rows = await (await c.request.get(origin + '/api/v1/cases')).json();
  const item = rows.results.find(row => row.title === title);
  const assigned = JSON.parse(execFileSync(python, [path.join(__dirname, 'association_lawyer.py'), item.lawyerId], { encoding: 'utf8', windowsHide: true }));
  await login(lp, assigned.email); await expect(lp).toHaveURL(/\/advogado$/);
  await lp.locator('.case-list').getByRole('button', { name: new RegExp(title) }).click();
  await lp.getByRole('button', { name: 'Iniciar triagem' }).click();
  for (const label of [/Escopo compatível/, /Conflito de interesses/, /Informações suficientes/]) await lp.getByLabel(label).check();
  await lp.getByLabel('Justificativa visível ao cliente').fill('Caso aprovado após análise individual.');
  await lp.getByRole('button', { name: 'Aprovar caso e preparar procuração' }).click();
  await expect(lp.getByRole('heading', { name: 'Gerar procuração em PDF' })).toBeVisible();
  // Um documento enviado pelo advogado também pode ser a procuração revisada.
  // A fixture de scanner só aceita email de CLIENT; ela processa a fila isolada inteira.
  await upload(lp, customer, { ...proof, name: 'procuracao-especifica.pdf' });
  await lp.getByLabel('Etapas contratadas', { exact: true }).fill('Representação específica da ocorrência cadastrada.');
  await lp.getByLabel(/Documento verificado/).selectOption({ label: 'procuracao-especifica.pdf · v1' });
  await lp.getByRole('button', { name: 'Enviar procuração deste caso para assinatura' }).click();
  await expect(lp.locator('.case-detail > .cases-heading')).toContainText('Aguardando procuração');
  await cp.reload();
  await cp.locator('.case-list').getByRole('button', { name: new RegExp(title) }).click();
  await expect(cp.getByText(/Esta procuração pertence exclusivamente a este caso/)).toBeVisible();
  await cp.setViewportSize({ width: 390, height: 844 });
  await cp.screenshot({ path: path.join(root, '.local/association-client-mobile.png'), fullPage: true });
  await upload(cp, customer, { ...proof, name: 'procuracao-assinada.pdf' });
  await cp.getByLabel(/Documento verificado/).selectOption({ label: 'procuracao-assinada.pdf · v1' });
  await cp.getByRole('button', { name: 'Entregar procuração assinada' }).click();
  await lp.reload(); await lp.locator('.case-list').getByRole('button', { name: new RegExp(title) }).click();
  await lp.getByLabel('Conferi a procuração assinada').check();
  await lp.getByRole('button', { name: 'Confirmar procuração', exact: true }).click();
  await expect(lp.locator('.case-detail > .cases-heading')).toContainText('Em preparação');
  await lp.screenshot({ path: path.join(root, '.local/association-lawyer.png'), fullPage: true });
  await c.close(); await l.close();
});

test('landing e checkout explicam adesão, análise e procuração posterior', async ({ page }) => {
  test.skip(process.env.IUSTUS_E2E_ASSOCIATION !== 'true', 'Requer o perfil de associação');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(origin);
  await expect(page.getByText('Conte o que aconteceu', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(root, '.local/association-landing-mobile.png'), fullPage: true });
  await page.goto(origin + '/checkout');
  await expect(page.getByRole('button', { name: /Pagar · 10x de/ })).toBeDisabled();
  await expect(page.getByText(/O pagamento online ainda não está disponível/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(root, '.local/association-checkout-mobile.png'), fullPage: true });
});
