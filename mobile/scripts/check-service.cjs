const { build } = require('../eas.json');
const origin = process.env.EXPO_PUBLIC_API_ORIGIN || build.production.env.EXPO_PUBLIC_API_ORIGIN;
async function get(path) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(origin + path, { signal: AbortSignal.timeout(30000), redirect: 'error' });
      if (response.status >= 500 && attempt < 2) continue;
      return { status: response.status, body: await response.json() };
    } catch (error) { if (attempt === 2) throw error; }
  }
}
async function main() {
  const url = new URL(origin);
  if (url.protocol !== 'https:' || url.username || url.password || url.origin !== origin) throw new Error('Use uma origem HTTPS sem caminho ou credenciais.');
  const [context, plan, protectedRoute] = await Promise.all([
    get('/api/v1/mobile/auth/context'), get('/api/v1/mobile/billing/plan'), get('/api/v1/mobile/dashboard'),
  ]);
  if (context.status !== 200 || typeof context.body.checkoutAvailable !== 'boolean' || typeof context.body.registrationAvailable !== 'boolean') throw new Error('Contexto mobile indisponível ou incompatível.');
  if (plan.status !== 200 || typeof plan.body.available !== 'boolean') throw new Error('Plano mobile indisponível ou incompatível.');
  if (protectedRoute.status !== 401) throw new Error('A rota privada não respondeu com a exigência de autenticação esperada.');
  console.log(`API mobile disponível em ${origin}; acesso privado protegido.`);
  console.log(`Cadastro: ${context.body.registrationAvailable ? 'aberto' : 'por ativação'}; checkout mobile: ${context.body.checkoutAvailable ? 'habilitado' : 'desabilitado'}; pagamento: ${plan.body.sandbox ? 'sandbox' : 'produção'}.`);
  console.log('Consultas públicas somente. Nenhum login, pagamento ou e-mail foi disparado.');
}
main().catch(error => { console.error('Verificação do serviço falhou: ' + error.message); process.exitCode = 1; });
