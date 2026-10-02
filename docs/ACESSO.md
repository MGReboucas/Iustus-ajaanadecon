# Acesso exclusivo da equipe

Atualizado em 02/10/2026. O sistema usa uma única origem para login e painel. Cadastro público e acesso de clientes não estão disponíveis na configuração local ou produtiva.

## Configuração

- `IUSTUS_PUBLIC_ORIGIN`: endereço do frontend, igual no backend e frontend. Local: `http://localhost:3000`. Produção: origem HTTPS sem caminho.
- `IUSTUS_INITIAL_ADMIN_EMAIL`: e-mail do administrador inicial, somente no backend.
- `DJANGO_API_ORIGIN` e `IUSTUS_PROXY_SECRET`: conexão privada do proxy com a API.
- Banco, chave Django, chave Fernet e SMTP continuam necessários. Consulte [implantação](../infra/deploy/README.md).

Remova as antigas variáveis `IUSTUS_CLIENT_ORIGIN` e `IUSTUS_TEAM_ORIGIN`. O endereço da API é infraestrutura; não é um segundo portal.

## Ativação inicial

Na raiz do projeto, depois de configurar o backend e aplicar as migrações:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py bootstrap_admin --name "Administrador"
backend/.venv/Scripts/python.exe backend/manage.py deliver_identity_mail
```

O comando registra uma conta sem senha utilizável e enfileira um link de ativação válido por 24 horas. O destinatário confirma a posse do e-mail ao usar o link e definir a senha. Depois entra e configura o autenticador TOTP. Guarde os códigos de recuperação exibidos uma única vez.

O comando pode reenviar a ativação enquanto a conta inicial estiver pendente, invalidando o link anterior. Não promove contas existentes nem modifica um administrador já ativado. Alterar ou digitar o e-mail da variável nunca concede privilégios por si só.

Em desenvolvimento, as mensagens ficam em `.local/mail/`. Em produção, o worker `run_operations` entrega por SMTP. Não publique tokens, senhas ou arquivos de configuração.

## Iniciar localmente

Execute em terminais separados:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload
npm.cmd run dev
backend/.venv/Scripts/python.exe backend/manage.py run_operations
```

Abra `http://localhost:3000`. A raiz encaminha para `/acessar`; o painel da equipe fica em `/advogado`. As antigas páginas do cliente e checkout encaminham para o login.

## Aprovação e revogação

No painel do administrador, **Aprovar profissional** registra um advogado autorizado no banco e envia o convite. A conta fica sem senha e sem e-mail confirmado até a ativação. Repetir o e-mail no formulário reenvia a ativação pendente e invalida o link anterior.

**Gestão de usuários** exibe contas ativas, pendentes de ativação e revogadas. A revogação invalida as sessões em todas as próximas requisições, desafios MFA e tokens pendentes. Casos ativos não impedem o bloqueio: os dados permanecem disponíveis para redistribuição pelo administrador. Reaprovar exige novo login; contas ainda não ativadas precisam de um novo convite.

A conta administrativa é protegida contra revogação pelo próprio painel. Recuperação excepcional de MFA e gestão adicional de administradores continuam sendo operações do servidor.

Profissionais ativos já existentes são preservados como autorizados. Revise a lista antes de liberar a equipe. Contas de clientes permanecem no banco para preservar vínculos com casos, mas não conseguem entrar.

## Segurança e validação

O backend verifica identidade, estado ativo, confirmação de e-mail, versão de autorização, MFA e validade da sessão a cada operação autenticada. Permissões por papel continuam aplicadas às ações administrativas e aos casos. CSRF também é exigido no login; cookies privados e limites de tentativas permanecem ativos.

Não há migração de esquema nesta alteração. Execute a suíte do backend a partir de `backend`: ` .venv/Scripts/python.exe manage.py test tests --settings=config.settings.test --noinput`. Os testes de concorrência exigem `config.settings.test_postgres`.

Os testes de navegador atuais cobrem o endereço único, bloqueio de clientes, convite, MFA e revogação. A jornada antiga dos dois portais foi preservada em `tests/e2e/access-dual-portal.legacy.cjs` como referência histórica e não é executada.

## Acesso simplificado para testes

`IDENTITY_MFA_REQUIRED=false` no backend permite acesso da equipe com e-mail verificado e senha, sem autenticador. A mesma regra vale para a seleção de profissionais. Permissões, CSRF, expiração e revogação de sessões continuam ativas. O padrão é `true`; reativar essa exigência invalida sessões que entraram apenas com senha.
