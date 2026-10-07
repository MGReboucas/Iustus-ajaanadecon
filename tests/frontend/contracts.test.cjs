const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('../../frontend/node_modules/typescript');
const source = fs.readFileSync(path.join(__dirname, '../../contracts/validation.ts'), 'utf8');
const code = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText;
const validators = {};
new Function('exports', code)(validators);
test('invalid billing responses cannot prepare checkout', () => {
  const plan = {amount: 69990, installments: 10, planVersion: 'v2', policyVersion: 'terms', available: true, sandbox: true};
  assert.equal(validators.isBillingPlan(plan), true);
  for (const value of [null, {}, {...plan, amount: '69990'}, {...plan, amount: -1},
      {...plan, installments: 0}, {...plan, installments: 13}, {...plan, amount: 69991},
      {...plan, available: 'true'}, {...plan, planVersion: ''}, {...plan, policyVersion: null}]) {
    assert.equal(validators.isBillingPlan(value), false);
  }
});
test('malformed expired or professional login cannot be persisted by mobile', () => {
  const login = {token: 'x'.repeat(43), expiresAt: new Date(Date.now()+3600000).toISOString(),
    user: {id: 'synthetic', name: '', email: 'test@example.test', role: 'CLIENT', caseEmailEnabled: true}};
  assert.equal(validators.isMobileLogin(login), true);
  for (const value of [null, {}, {...login, token: ''}, {...login, expiresAt: 'invalid'},
      {...login, expiresAt: '2000-01-01T00:00:00Z'}, {...login, user: {...login.user, role: 'ADMIN'}},
      {...login, user: {...login.user, caseEmailEnabled: 'true'}}]) {
    assert.equal(validators.isMobileLogin(value), false);
  }
});
