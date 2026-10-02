# Jornadas de acesso e atendimento

Os testes usam banco isolado `iustus_e2e` e contas sintéticas `e2e-*@example.test`. Nunca executar fixtures contra o banco publicado.

- `access.spec.cjs`: convite profissional, MFA quando habilitado, recuperação e revogação.
- `shared-portal.spec.cjs`: cadastro e confirmação do cliente, login por perfil, rascunho, liberação administrativa, distribuição e triagem no mesmo site. Executar com `IDENTITY_MFA_REQUIRED=false`.

Preparar com `python tests/e2e/fixture.py prepare` e executar `npm run test:e2e`. Em Windows usar o Python de `backend/.venv/Scripts/python.exe`. `IUSTUS_E2E_SQLITE=true` permite o banco SQLite isolado em `.local`; concorrência deve ser testada separadamente no PostgreSQL. `PLAYWRIGHT_CHANNEL=chrome` usa Chrome instalado.

A CI executa as duas modalidades de MFA. E-mails de teste ficam em memória/na fila isolada; nenhum destinatário real é usado. Traces e screenshots automáticos estão desativados para não persistir tokens ou senhas.
