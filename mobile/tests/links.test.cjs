const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const source = fs.readFileSync(path.join(__dirname, '../src/lib/links.ts'), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
function parser(origin = 'https://www.iustus.app') {
  const exports = {};
  new Function('exports', 'require', code)(exports, name => name === './api' ? { apiOrigin: () => origin } : { Linking: {} });
  return exports.readAccessLink;
}
test('email links support canonical domain, apex and native access without altering tokens', () => {
  const read = parser();
  for (const mode of ['verify', 'reset', 'member']) {
    for (const base of ['https://www.iustus.app/acessar', 'https://iustus.app/acessar', 'iustus://access', 'iustus:///access']) {
      assert.deepEqual(read(`${base}#${mode}=${'a'.repeat(43)}`), { mode, token: 'a'.repeat(43) });
    }
  }
});
test('rejects untrusted hosts, arbitrary paths, mixed tokens and credentials', () => {
  const read = parser(); const token = 'a'.repeat(43);
  for (const base of ['https://evil.test/acessar', 'https://www.iustus.app.evil.test/acessar', 'https://www.iustus.app/other', 'iustus://other', 'https://user:secret@www.iustus.app/acessar', 'http://www.iustus.app/acessar']) {
    assert.throws(() => read(`${base}#reset=${token}`));
  }
  assert.throws(() => read(`https://www.iustus.app/acessar#reset=${token}&verify=${token}`));
  assert.throws(() => read(`https://www.iustus.app/acessar#reset=${token}&reset=${token}`));
  assert.throws(() => parser('https://staging.example.test')(`https://www.iustus.app/acessar#reset=${token}`));
});
