const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const source = fs.readFileSync(path.join(__dirname, '../src/lib/api.ts'), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
function load(fetch, origin = 'https://app.example.test', development = false) {
  const exports = {};
  new Function('exports', 'process', '__DEV__', 'fetch', code)(exports, { env: { EXPO_PUBLIC_API_ORIGIN: origin } }, development, fetch);
  return exports;
}

test('credentials require HTTPS outside local development', () => {
  const { resolveOrigin } = load();
  assert.equal(resolveOrigin('https://app.example.test/', false), 'https://app.example.test');
  assert.equal(resolveOrigin('http://192.168.1.20:3000', true), 'http://192.168.1.20:3000');
  for (const url of ['http://app.example.test', 'https://user:password@app.example.test', 'https://app.example.test/path', 'https://app.example.test?token=bad', undefined]) {
    assert.throws(() => resolveOrigin(url, false), /conectado/);
  }
  assert.throws(() => resolveOrigin('http://192.168.1.20:3000', false));
  assert.throws(() => resolveOrigin('http://public.example.test', true));
});

test('intake uses PATCH, idempotency and binary transport without changing credential boundary', async () => {
  const id = '00000000-0000-0000-0000-000000000001';
  const calls = [];
  const { request, validRoute } = load(async (url, options) => {
    calls.push({ url, options });
    return options.method === 'GET' ? new Response('%PDF-test') : Response.json({ ok: true });
  });
  await request(`cases/${id}`, 'token', { version: 2 }, { method: 'PATCH' });
  await request(`cases/${id}/submit`, 'token', { version: 3 }, { idempotencyKey: 'synthetic-retry-001' });
  const bytes = new TextEncoder().encode('binary-content').buffer;
  await request(`uploads/${id}/content`, 'token', bytes, { binary: true });
  const downloaded = await request(`documents/${id}/versions/${id}/content`, 'token', undefined, { download: true });
  assert.equal(calls[0].options.method, 'PATCH');
  assert.equal(calls[1].options.headers['Idempotency-Key'], 'synthetic-retry-001');
  assert.equal(calls[2].options.headers['Content-Type'], 'application/octet-stream');
  assert.equal(calls[2].options.body, bytes);
  assert.equal(new TextDecoder().decode(downloaded), '%PDF-test');
  for (const call of calls) { assert.equal(call.options.credentials, 'omit'); assert.equal(call.options.headers.Authorization, 'Bearer token'); }
  for (const path of ['cases/catalog', `cases/${id}/requests/${id}/response`, 'privacy/requests', `notifications/${id}/read`]) assert.equal(validRoute(path), true);
  for (const path of ['cases/not-a-uuid', `cases/${id}/assignment`, 'billing/checkout', 'https://evil.test', `cases/${id}/../admin`, 'auth/mfa/enroll']) assert.equal(validRoute(path), false);
});

test('native requests send bearer without cookies, only to mobile routes', async () => {
  let actual;
  const { request } = load(async (url, options) => { actual = { url, options }; return Response.json({ totalCases: 2 }); });
  assert.equal((await request('dashboard', 'synthetic')).totalCases, 2);
  assert.equal(actual.url, 'https://app.example.test/api/v1/mobile/dashboard');
  assert.equal(actual.options.headers.Authorization, 'Bearer synthetic');
  assert.equal(actual.options.credentials, 'omit');
  assert.equal(actual.options.redirect, 'error');
  await assert.rejects(request('../admin/users', 'synthetic'));
  await assert.rejects(request('https://evil.example.test', 'synthetic'));
});

test('login posts credentials without bearer and handles logout 204', async () => {
  const { request } = load(async (_, options) => {
    assert.equal(options.method, 'POST');
    assert.equal(options.headers.Authorization, undefined);
    assert.deepEqual(JSON.parse(options.body), { email: 'test@example.test', password: 'synthetic' });
    return new Response(null, { status: 204 });
  });
  assert.equal(await request('auth/login', undefined, { email: 'test@example.test', password: 'synthetic' }), undefined);
});

test('preserves session expiry and reports malformed responses or network errors safely', async () => {
  const expired = load(async () => Response.json({ error: { code: 'AUTH_REQUIRED', message: 'Entre novamente.' } }, { status: 401 }));
  await assert.rejects(expired.request('dashboard', 'synthetic'), err => err.status === 401 && err.code === 'AUTH_REQUIRED');
  const invalid = load(async () => new Response('<html>internal debug</html>'));
  await assert.rejects(invalid.request('dashboard'), err => err.code === 'INVALID_RESPONSE' && !err.message.includes('debug'));
  const offline = load(async () => { throw new Error('internal network detail'); });
  await assert.rejects(offline.request('dashboard'), err => err.code === 'NETWORK_ERROR' && !err.message.includes('internal'));
});
