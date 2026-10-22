# Infraestrutura

Configurações operacionais do mesmo repositório; sem deploy, domínio ou recurso externo criado.

## PostgreSQL nativo do projeto

### Ambiente Windows preparado em 22/10/2026

Na raiz, `npm.cmd run local:start` inicia PostgreSQL isolado, ClamAV, API,
worker e frontend em segundo plano. Abra http://localhost:3000/acessar.
`npm.cmd run local:stop` encerra os processos registrados pelo projeto;
o banco continua ativo e os dados são preservados. Execute `npm.cmd run build`
depois de alterar o frontend para atualizar a versão servida.

Os scripts pressupõem as dependências instaladas em `frontend/node_modules`,
`mobile/node_modules` e `backend/.venv`, configuração gerada por `setup_local.py`
e PostgreSQL 18 em `C:\Program Files\PostgreSQL\18\bin`. Para outra instalação,
passe `-PostgresBin` diretamente a `infra/start-local.ps1`.

Dados, logs, processos e e-mails ficam em `.local/`, ignorado pelo Git.
O primeiro acesso do administrador está em `.local/primeiro-acesso.txt`:
abra o link para definir a senha e configurar MFA. Se expirar antes da ativação,
execute `backend/.venv/Scripts/python.exe backend/manage.py bootstrap_admin`;
o worker grava a nova mensagem em `.local/mail/`. Não publique esses arquivos.

O scanner portátil está em `.local/clamav/clamav-1.4.6.win.x64`, ouvindo
somente em `127.0.0.1:3310`. Para atualizar as assinaturas, execute nessa pasta
`./freshclam.exe --config-file=freshclam.conf --quiet` e reinicie os serviços.
Binários e assinaturas vêm do [ClamAV oficial](https://www.clamav.net/downloads).
Sem scanner, documentos permanecem em quarentena.

Validação realizada: build Next.js, 182 testes backend com PostgreSQL,
13 testes frontend, duas jornadas web no Edge, tipos/lint e cinco testes mobile,
seis jornadas mobile no Edge com API simulada e exportação Android/iOS/web.
O scanner real foi exercitado com conteúdo limpo pelo protocolo INSTREAM.

PagBank permanece desabilitado; cobrança real depende das credenciais e
homologação do provedor. E-mails são arquivos locais. O aplicativo nativo
ainda precisa ser validado em aparelho e não foi publicado nas lojas.
Para desenvolvimento mobile, use `npm.cmd run mobile:start`; a URL localhost
configurada serve à prévia nesta máquina, não a um telefone físico.

O [guia de acesso](../docs/ACESSO.md) usa setup_local.py para iniciar um cluster isolado em .local/postgres, porta 55432, com credenciais aleatórias ignoradas pelo Git. O serviço PostgreSQL preexistente é preservado.

## PostgreSQL via Docker (alternativa)

Com Docker e Compose instalados, executar na raiz:

```bash
docker compose -f infra/compose.local.yaml up -d postgres
docker compose -f infra/compose.local.yaml ps
docker compose -f infra/compose.local.yaml stop
```

O banco fica em `127.0.0.1:5432`; usuário/banco `iustus`, senha exclusivamente local `iustus-local-only`. Os dados ficam no volume nomeado. A configuração é compatível com `backend/.env.example`. Não usar em produção nem remover o volume para reiniciar o serviço.

## Implantação futura

`proxy/` contém as decisões da entrada HTTPS; `deploy/` concentra o roteiro para frontend, API e worker. A escolha de provedor, TLS, objetos, scanner, backups e segredos permanece pendente. A configuração produtiva será criada após homologação dos controles de acesso locais e definição dos controles de operação.
