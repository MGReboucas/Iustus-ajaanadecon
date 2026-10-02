# Acesso e atendimento no portal único

Atualizado em 02/10/2026.

O mesmo site atende clientes, advogados e administradores. `/acessar` oferece cadastro de cliente, confirmação de e-mail, login e recuperação de senha. Após o login, o papel salvo no banco determina o destino: cliente em `/cliente`; advogado e administrador em `/advogado`. O cadastro público nunca cria profissionais ou administradores.

## Jornada de atendimento

1. Cliente cadastra nome, e-mail e senha; confirma o e-mail pelo link recebido.
2. Cliente entra no painel e salva um rascunho de caso.
3. Administrador libera atendimento para esse e-mail, com validade e justificativa.
4. Cliente envia o caso à triagem.
5. Administrador distribui o caso para um advogado ativo.
6. Advogado inicia a triagem, pede complementos e registra a decisão; cliente acompanha o histórico e as mensagens.

Cadastro não gera cobrança nem assinatura. O checkout continua em preparação. Arquivos só podem ser enviados quando o armazenamento privado e o scanner estiverem configurados; a interface informa a indisponibilidade.

## Equipe

O administrador aprova profissionais no painel. O convite cria uma conta LAWYER pendente e envia um link para definir nome e senha. Revogação de acesso invalida sessões e tokens. O administrador inicial é criado pelo comando `bootstrap_admin`, usando `IUSTUS_INITIAL_ADMIN_EMAIL`; contas existentes nunca são promovidas por cadastro público.

`IDENTITY_MFA_REQUIRED=false` permite login por senha durante os testes, conforme autorização do responsável. O padrão do código é `true`. Reativar MFA invalida sessões que entraram só com senha. CSRF, verificação de e-mail, permissões e revogação continuam ativos nas duas modalidades.

## Configuração

- `DJANGO_SETTINGS_MODULE=config.settings.production` no servidor.
- `IUSTUS_PUBLIC_ORIGIN`: origem HTTPS do frontend; a mesma para os dois perfis.
- `DJANGO_ALLOWED_HOSTS`: hostname exato da API.
- `DJANGO_API_ORIGIN` e `IUSTUS_PROXY_SECRET`: conexão privada do proxy Next.js com o Django.
- PostgreSQL, chave Django, chave Fernet e SMTP persistentes no gerenciador de ambiente.

A escolha do papel é feita pelo backend após autenticação. Cabeçalhos do navegador não escolhem privilégios. A sessão é validada contra o usuário, versão de autorização, validade e política de MFA.

## E-mails

A aplicação grava os e-mails numa fila durável no PostgreSQL. `python manage.py run_operations` entrega essa fila, agenda lembretes e processa tarefas. É necessário manter esse processo ativo. E-mails não são enviados automaticamente só porque o serviço web está online.

O serviço gratuito do Render não permite SMTP nas portas usuais. Sem worker hospedado, é possível executar temporariamente o worker em uma máquina autorizada durante testes; desligar a máquina interrompe o envio, e a fila permanece no banco. Não armazenar segredos em arquivos versionados.

## Verificação

- Backend: `python manage.py test tests --settings=config.settings.test --noinput`, dentro de `backend`.
- Frontend: `npm run build`.
- Navegador: `npm run test:e2e`; repetir com `IDENTITY_MFA_REQUIRED=false` para a jornada compartilhada de cadastro, liberação, distribuição e triagem.
- Produção: `node infra/deploy/check_web.cjs https://iustus-defesa-juridica.vercel.app`.

Os testes de navegador usam exclusivamente banco isolado e contas sintéticas. Não usar informações reais de clientes nos testes.
