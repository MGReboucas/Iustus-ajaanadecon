# Testes de navegador

A suíte atual valida o endereço único da equipe: aprovação pelo administrador, ativação por e-mail, senha, MFA, código de recuperação, revogação de sessão, bloqueio de clientes e proteção CSRF. A jornada antiga de dois portais está preservada em `access-dual-portal.legacy.cjs`, fora da execução atual; as regras de casos continuam cobertas no backend.

Use exclusivamente um PostgreSQL local de testes em `DATABASE_URL`. O fixture cria `iustus_e2e`; nunca execute com a URL do banco de produção. Configure `IUSTUS_PUBLIC_ORIGIN=http://localhost:3000` para o runner e frontend.

Execute `python tests/e2e/fixture.py prepare`, `npm run build` e `npm run test:e2e` pela raiz. O runner inicia e encerra seus servidores nas portas 3000/8000. No Windows, `PLAYWRIGHT_CHANNEL=msedge` usa o Edge instalado. Traces e screenshots automáticos são desativados para não persistir tokens e MFA.

Alternativa para validar a interface sem PostgreSQL: defina `IUSTUS_E2E_SQLITE=true` antes do preparo e da execução. Isso usa exclusivamente `.local/iustus_e2e.sqlite3`; não valida concorrência PostgreSQL. A CI continua usando PostgreSQL.
