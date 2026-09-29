// Verifica o serviço de acesso e a sessão CSRF sem cadastrar nem enviar e-mail.
// node infra/deploy/check_web.cjs https://cliente.example https://equipe.example
const origins = process.argv.slice(2);
if (origins.length !== 2) throw new Error('Informe as origens HTTPS de cliente e equipe.');
async function check(origin, portal) {
  const url = new URL(origin);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new Error('Use origens HTTPS, sem credenciais, caminho ou parâmetros.');
  const readiness = await fetch(new URL('/api/v1/ready', url), { redirect: 'error', signal: AbortSignal.timeout(30000) });
  if (!readiness.ok || (await readiness.json()).status !== 'ok') throw new Error(`${portal}: API ou banco indisponível (${readiness.status}).`);
  const response = await fetch(new URL('/api/v1/auth/csrf', url), { redirect: 'error', signal: AbortSignal.timeout(30000) });
  const body = await response.json();
  if (!response.ok || body.portal !== portal || !body.csrfToken) throw new Error(`${portal}: serviço de acesso indisponível (${response.status}, ${body.error?.code || 'resposta inválida'}).`);
  const cookies = response.headers.getSetCookie();
  if (!cookies.some(cookie => cookie.startsWith('__Host-iustus_csrf=') && /;\s*Secure(?:;|$)/i.test(cookie) && /;\s*Path=\//i.test(cookie) && !/;\s*Domain=/i.test(cookie))) throw new Error(`${portal}: cookie CSRF sem proteção esperada.`);
  if (!response.headers.get('cache-control')?.includes('no-store')) throw new Error(`${portal}: resposta de acesso pode ser armazenada em cache.`);
  const protectedResponse = await fetch(new URL(`/api/v1/dashboard/${portal}`, url), { redirect: 'error', signal: AbortSignal.timeout(30000) });
  const protectedBody = await protectedResponse.json();
  if (protectedResponse.status !== 403 || protectedBody.error?.code !== 'AUTH_REQUIRED') throw new Error(`${portal}: painel anônimo não foi recusado como esperado.`);
  console.log(`${portal}: API/banco, configuração, CSRF seguro, cache privado e bloqueio de anônimo OK.`);
}
(async () => {
  if (new URL(origins[0]).host === new URL(origins[1]).host) throw new Error('Os portais devem ter hosts distintos.');
  await check(origins[0], 'client');
  await check(origins[1], 'team');
})().catch(error => { console.error(error.message); process.exit(1); });
