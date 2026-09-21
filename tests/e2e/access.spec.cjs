const { test, expect } = require('../../frontend/node_modules/@playwright/test');
const { execFileSync } = require('node:child_process');
const { createHmac, randomUUID } = require('node:crypto');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const python = process.env.IUSTUS_TEST_PYTHON || path.join(root, 'backend', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const password = 'Synthetic-Browser-Passphrase-938!';
const clientOrigin = 'http://localhost:3000';
const teamOrigin = 'http://127.0.0.1:3000';
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

test('cliente cadastra, verifica e-mail, acessa painel e redefine senha', async ({ page }) => {
  const address = email();
  await page.goto(clientOrigin + '/acessar');
  await page.getByRole('button', { name: 'Criar conta', exact: true }).click();
  await page.getByLabel('Nome completo').fill('Cliente de Teste');
  await page.getByLabel('E-mail', { exact: true }).fill(address);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Criar minha conta' }).click();
  await expect(page.getByRole('status')).toContainText('Confira seu e-mail');
  await page.goto(mailLink(address));
  await page.getByRole('button', { name: 'Confirmar meu e-mail' }).click();
  await expect(page.getByRole('status')).toContainText('E-mail confirmado');
  await signIn(page, clientOrigin, address);
  await expect(page.getByRole('heading', { name: 'Olá, Cliente de Teste.' })).toBeVisible();
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await expect(page).toHaveURL(/\/acessar$/);
  await page.getByRole('button', { name: 'Esqueci minha senha' }).click();
  await page.getByLabel('E-mail', { exact: true }).fill(address);
  await page.getByRole('button', { name: 'Enviar recuperação' }).click();
  await expect(page.getByRole('status')).toContainText('instruções');
  await page.goto(mailLink(address));
  const changed = 'Changed-Browser-Passphrase-651!';
  await page.getByLabel('Nova senha').fill(changed);
  await page.getByRole('button', { name: 'Salvar nova senha' }).click();
  await expect(page.getByRole('status')).toContainText('Senha atualizada');
  await signIn(page, clientOrigin, address, changed);
  await expect(page.getByRole('heading', { name: 'Olá, Cliente de Teste.' })).toBeVisible();
});

test('administrador confirma MFA, convida advogado e usa recuperação uma vez', async ({ browser }) => {
  const admin = email(), lawyer = email();
  fixture('admin', admin);
  const context = await browser.newContext();
  const page = await context.newPage();
  await signIn(page, teamOrigin, admin);
  const codes = await enroll(page);
  await page.getByLabel('E-mail do profissional').fill(lawyer);
  await page.getByRole('button', { name: 'Enviar convite' }).click();
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
  await expect(professional.getByRole('heading', { name: 'Convidar advogado' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Sair da conta' }).click();
  await expect(page).toHaveURL(/\/acessar$/);
  await signIn(page, teamOrigin, admin);
  await page.getByLabel('Código do autenticador ou de recuperação').fill(codes[0]);
  await page.getByRole('button', { name: 'Confirmar segundo fator' }).click();
  await expect(page.getByRole('heading', { name: 'Olá, Admin Teste.' })).toBeVisible();
  await other.close(); await context.close();
});

test('rotas e headers de outro portal são recusados', async ({ request }) => {
  expect((await request.get(clientOrigin + '/advogado')).status()).toBe(403);
  expect((await request.get(teamOrigin + '/cliente')).status()).toBe(403);
  const result = await request.get(clientOrigin + '/api/v1/auth/csrf', {
    headers: { 'X-Forwarded-Host': '127.0.0.1:3000', 'X-Iustus-Portal-Host': '127.0.0.1:3000', 'X-Iustus-Proxy-Key': 'forged' },
  });
  expect((await result.json()).portal).toBe('client');
  const login = await request.post(clientOrigin + '/api/v1/auth/login', { data: { email: email(), password } });
  expect(login.status()).toBe(403);
  expect((await login.json()).error.code).toBe('CSRF_FAILED');
  const binary = { headers: { 'Content-Type': 'application/octet-stream' }, data: Buffer.from('test') };
  expect((await request.post(clientOrigin + '/api/v1/cases', binary)).status()).toBe(415);
  expect((await request.post(clientOrigin + `/api/v1/uploads/${randomUUID()}/content`, binary)).status()).toBe(403);
  const tooLarge = await request.post(clientOrigin + `/api/v1/uploads/${randomUUID()}/content`, {
    headers: binary.headers, data: Buffer.alloc(20 * 1024 * 1024 + 1),
  });
  expect(tooLarge.status()).toBe(413);
});

test('caso percorre rascunho, distribuição, complemento e aceite com isolamento', async ({ browser }) => {
  test.setTimeout(90000);
  const clientEmail = email(), adminEmail = email(), lawyerEmail = email();
  fixture('client', clientEmail); fixture('admin', adminEmail); fixture('lawyer', lawyerEmail);
  const clientContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const adminContext = await browser.newContext();
  const lawyerContext = await browser.newContext();
  const clientPage = await clientContext.newPage(), adminPage = await adminContext.newPage(), lawyerPage = await lawyerContext.newPage();
  await signIn(clientPage, clientOrigin, clientEmail);
  await clientPage.getByRole('button', { name: 'Novo caso', exact: true }).click();
  await clientPage.getByLabel('Título do caso').fill('Cobrança contratual fictícia');
  await clientPage.getByLabel('Categoria', { exact: true }).selectOption('CONTRACTS');
  await clientPage.getByLabel('Relato', { exact: true }).fill('Informação privada de um contrato inteiramente fictício para testar a triagem.');
  await clientPage.getByLabel('Estou ciente de que família e sucessões não fazem parte do serviço.').check();
  await clientPage.getByRole('button', { name: 'Salvar rascunho', exact: true }).click();
  await expect(clientPage.getByRole('status')).toHaveText('Alteração registrada.');
  await expect(clientPage.getByRole('button', { name: 'Enviar para triagem' })).toBeDisabled();
  fixture('case-grant', clientEmail);
  await clientPage.reload();
  await clientPage.getByRole('button', { name: /Cobrança contratual fictícia/ }).click();
  const pdf = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n');
  await clientPage.getByLabel('Arquivo para anexar').setInputFiles({ name: 'contrato-ficticio.pdf', mimeType: 'application/pdf', buffer: pdf });
  await clientPage.getByRole('button', { name: 'Enviar arquivo', exact: true }).click();
  await expect(clientPage.getByText('Arquivo recebido. Aguarde a verificação e atualize a lista.')).toBeVisible();
  await expect(clientPage.getByRole('button', { name: 'Baixar contrato-ficticio.pdf (v1)', exact: true })).toBeDisabled();
  expect(fixture('document-scan-fixture', clientEmail).available).toBe(1);
  await clientPage.getByRole('button', { name: 'Atualizar documentos', exact: true }).click();
  await expect(clientPage.getByRole('button', { name: 'Baixar contrato-ficticio.pdf (v1)', exact: true })).toBeEnabled();
  const downloadEvent = clientPage.waitForEvent('download');
  await clientPage.getByRole('button', { name: 'Baixar contrato-ficticio.pdf (v1)', exact: true }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe('contrato-ficticio.pdf');
  expect(await download.failure()).toBeNull();
  await clientPage.getByRole('button', { name: 'Enviar para triagem' }).click();
  await expect(clientPage.locator('.case-detail > .cases-heading > .case-badge')).toHaveText('Enviado para distribuição');
  const reference = (await clientPage.locator('#case-detail-title').innerText()).replace('Caso ', '');
  await signIn(lawyerPage, teamOrigin, lawyerEmail); await enroll(lawyerPage);
  await expect(lawyerPage.getByText('Nenhum caso encontrado neste filtro.')).toBeVisible();
  await signIn(adminPage, teamOrigin, adminEmail); await enroll(adminPage);
  await adminPage.getByRole('button', { name: new RegExp(`Caso ${reference}`) }).click();
  await expect(adminPage.getByText('Informação privada de um contrato', { exact: false })).toHaveCount(0);
  await adminPage.getByLabel('Advogado responsável').selectOption({ label: `Advogado Teste — ${lawyerEmail}` });
  await adminPage.getByLabel('Motivo administrativo').fill('Distribuição privada que não deve aparecer ao cliente.');
  await adminPage.getByRole('button', { name: 'Salvar responsável' }).click();
  await expect(adminPage.getByRole('status')).toHaveText('Alteração registrada.');
  await lawyerPage.reload();
  await lawyerPage.getByRole('button', { name: /Cobrança contratual fictícia/ }).click();
  await lawyerPage.getByRole('button', { name: 'Iniciar triagem' }).click();
  await lawyerPage.getByLabel('Informações a complementar').fill('Informe quando ocorreu o fato fictício.');
  await lawyerPage.getByRole('button', { name: 'Solicitar complemento' }).click();
  await expect(lawyerPage.locator('.case-detail > .cases-heading > .case-badge')).toHaveText('Aguardando complemento');
  await clientPage.reload();
  await clientPage.getByRole('button', { name: /Cobrança contratual fictícia/ }).click();
  await clientPage.getByLabel('Sua resposta').fill('O fato fictício ocorreu em quinze de setembro.');
  await clientPage.getByLabel('Anexar contrato-ficticio.pdf (v1)', { exact: true }).check();
  await clientPage.getByRole('button', { name: 'Enviar complemento', exact: true }).click();
  await expect(clientPage.getByText('Aguardando conferência pelo responsável.')).toBeVisible();
  await expect(clientPage.getByText('Distribuição privada que não deve aparecer ao cliente.')).toHaveCount(0);
  expect(await clientPage.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  if (process.env.IUSTUS_CASE_SCREENSHOT) await clientPage.screenshot({ path: process.env.IUSTUS_CASE_SCREENSHOT, fullPage: true });
  await lawyerPage.reload();
  await lawyerPage.getByRole('button', { name: /Cobrança contratual fictícia/ }).click();
  await expect(lawyerPage.getByRole('button', { name: 'Anexo: contrato-ficticio.pdf (v1)', exact: true })).toBeVisible();
  const lawyerDownload = lawyerPage.waitForEvent('download');
  await lawyerPage.getByRole('button', { name: 'Anexo: contrato-ficticio.pdf (v1)', exact: true }).click();
  expect((await lawyerDownload).suggestedFilename()).toBe('contrato-ficticio.pdf');
  await lawyerPage.getByLabel('Resultado da conferência').fill('Data recebida e conferida para o teste.');
  await lawyerPage.getByRole('button', { name: 'Conferir e retomar triagem' }).click();
  await lawyerPage.getByLabel('Escopo compatível:', { exact: false }).check();
  await lawyerPage.getByLabel('Conflito de interesses analisado').check();
  await lawyerPage.getByLabel('Informações suficientes para decidir o atendimento').check();
  await lawyerPage.getByLabel('Justificativa visível ao cliente').fill('Aceite fictício após análise das informações e do escopo.');
  await lawyerPage.getByRole('button', { name: 'Aceitar caso', exact: true }).click();
  await expect(lawyerPage.locator('.case-detail > .cases-heading > .case-badge')).toHaveText('Aceito na triagem');
  await clientPage.reload();
  await clientPage.getByRole('button', { name: /Cobrança contratual fictícia/ }).click();
  await expect(clientPage.locator('.case-detail > .cases-heading > .case-badge')).toHaveText('Aceito na triagem');
  await expect(clientPage.getByText('Aceite fictício após análise das informações e do escopo.')).toBeVisible();
  await clientContext.close(); await adminContext.close(); await lawyerContext.close();
});
