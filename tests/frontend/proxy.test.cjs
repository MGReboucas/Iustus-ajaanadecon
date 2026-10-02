const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('../../frontend/node_modules/typescript');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../frontend/app/api/v1/[...path]/route.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
function handler(response) {
  const exports = {};
  const process = { env: { DJANGO_API_ORIGIN: 'https://api.example.test', IUSTUS_PUBLIC_ORIGIN: 'https://app.example.test', IUSTUS_PROXY_SECRET: 'synthetic-test-key' } };
  new Function('exports', 'require', 'fetch', 'process', compiled)(exports, () => ({}), async () => response, process);
  return exports.GET;
}
async function call(response, path = 'auth/csrf') {
  const request = new Request('https://app.example.test/api/v1/' + path, { headers: { host: 'app.example.test' } });
  request.nextUrl = new URL(request.url);
  return handler(response)(request, { params: Promise.resolve({ path: path.split('/') }) });
}
test('proxy hides debug text and HTML even when upstream returns 400', async () => {
  for (const type of ['text/plain', 'text/html']) {
    const result = await call(new Response('DisallowedHost INTERNAL_DETAILS', { status: 400, headers: { 'content-type': type } }));
    assert.equal(result.status, 502);
    assert.equal((await result.json()).error.code, 'UPSTREAM_ERROR');
  }
});
test('proxy preserves structured authentication errors', async () => {
  const body = { error: { code: 'INVALID_CREDENTIALS', message: 'Access denied' } };
  const result = await call(Response.json(body, { status: 403 }));
  assert.equal(result.status, 403);
  assert.deepEqual(await result.json(), body);
});
test('proxy preserves CSRF response and session cookies', async () => {
  const result = await call(Response.json({ csrfToken: 'synthetic', portal: 'team' }, { headers: { 'set-cookie': '__Host-iustus_csrf=synthetic; Secure; Path=/; SameSite=Lax' } }));
  assert.equal(result.status, 200);
  assert.equal((await result.json()).portal, 'team');
  assert.match(result.headers.get('set-cookie'), /Secure/);
});
test('proxy preserves authorized binary downloads', async () => {
  const id = '00000000-0000-0000-0000-000000000001';
  const result = await call(new Response('%PDF-synthetic', { headers: { 'content-type': 'application/pdf' } }), `documents/${id}/versions/${id}/content`);
  assert.equal(result.status, 200);
  assert.equal(await result.text(), '%PDF-synthetic');
});
