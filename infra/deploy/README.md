# Preparação e implantação

O repositório contém Dockerfile, settings de produção e Blueprint Render para API e worker. O frontend é Next.js, com implantação prevista na Vercel; o PostgreSQL previsto é externo (Neon). Estes arquivos não comprovam que os serviços externos foram criados ou homologados.

## Configuração

Use [production.env.example](production.env.example) como inventário. Cadastre os valores privados no gerenciador de ambiente de cada serviço; não os versione. API e worker precisam compartilhar banco, chave Fernet, chave Django, segredo do proxy, origens e SMTP. O frontend recebe somente as duas origens, DJANGO_API_ORIGIN e IUSTUS_PROXY_SECRET, além dos flags de checkout.

- Cliente e equipe exigem hosts HTTPS distintos.
- DJANGO_API_ORIGIN aponta para a origem HTTPS da API, sem caminho.
- DJANGO_ALLOWED_HOSTS contém hosts exatos da API.
- IDENTITY_ENCRYPTION_KEY deve permanecer estável entre releases; perdê-la impede decifrar dados já persistidos.
- SMTP deve ser autenticado. O worker entrega e-mails com tentativas limitadas.
- Cobranças reais permanecem bloqueadas até concluir assinatura e conciliação financeira.

O Blueprint inclui dois serviços pagos. Custos e contas ainda precisam ser confirmados antes de aplicar. A configuração de documentos é opcional e começa desabilitada.

## Verificações antes da publicação

Na raiz, execute:

```powershell
npm.cmd run typecheck
npm.cmd run build
npm.cmd run docs:check
npm.cmd run test:documents
backend/.venv/Scripts/python.exe backend/manage.py test tests --settings=config.settings.test --noinput
```

A suíte SQLite não substitui os testes de concorrência com PostgreSQL nem E2E. Ambos estão na CI; confirme os três jobs aprovados para o commit implantado.

No ambiente da API, com os segredos já injetados:

```sh
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py migrate --check
```

As advertências HSTS de subdomínios e preload são deliberadas durante a implantação inicial. Faça backup e avalie compatibilidade antes das migrações. O preDeployCommand do Render aplica migrações; não execute migrações concorrentes em API e worker.

## Processos e checagens

- API: comando Gunicorn do Dockerfile.
- Worker: `python manage.py run_operations`. Processa e-mails, lembretes, limpeza e um documento por ciclo quando o armazenamento estiver habilitado. Recicla conexões do banco a cada ciclo.
- ClamAV: serviço adicional em rede privada, a provisionar antes de habilitar documentos. Não está incluído no Blueprint.
- `/api/v1/health/`: liveness pública mínima, sem verificar dependências.
- `/api/v1/ready`: verifica uma consulta no banco, exige proxy confiável na API; o frontend expõe apenas estado genérico. Não comprova migrações, SMTP, S3 ou scanner.

Após publicar ambos os portais:

```sh
node infra/deploy/check_web.cjs https://cliente.example https://equipe.example
```

A checagem verifica API/banco, CSRF, cookies, cache e recusa de acesso anônimo aos painéis. Depois valide cadastro, confirmação de e-mail, recuperação, login e MFA com contas de homologação. Não use dados reais nesta validação.

## Documentos: bloqueio de infraestrutura conhecido

O proxy atual transporta arquivos de até 20 MiB pelo Next.js. A [documentação da Vercel](https://vercel.com/docs/functions/limitations) limita corpos de requisição de Functions a 4,5 MB. Portanto, habilitar S3 sozinho não torna esse fluxo pronto para produção na Vercel.

O código já oferece transferência direta autorizada para S3 com `DOCUMENT_DIRECT_UPLOAD_ENABLED=true`. Ela permanece desligada até homologação. Configure CORS usando [s3-cors.example.json](s3-cors.example.json), substituindo as origens de exemplo pelos dois portais reais.

A API autoriza PUT por 5 minutos para uma chave aleatória, com tamanho, checksum SHA-256, criptografia AES256 e `If-None-Match: *` assinados. O navegador envia os bytes diretamente ao bucket sem cookies. Depois, a API revalida acesso, prazo, tamanho, formato e hash; o documento entra em quarentena para o scanner. O bucket deve suportar SigV4, checksums e gravação condicional, além de bloquear acesso público. Não conceder GetObject/ListBucket ao navegador.

Uma URL de upload é uma credencial temporária: não registrar ou compartilhar; ela pode continuar aceitando o PUT até expirar mesmo se a sessão for revogada. A revogação impede confirmar o envio ou baixar o arquivo pela aplicação. Gravação condicional impede sobrescrever o objeto; conservar essa restrição também na política do bucket. Nenhuma URL de download S3 é exposta.

Downloads e exportações continuam autenticados e transmitidos em streaming pelo proxy. A [orientação da Vercel](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions) recomenda streaming para respostas grandes. Validar esse comportamento no ambiente hospedado, inclusive arquivos de 20 MiB e exportações grandes, antes de liberar clientes.

Testes locais usam S3 simulado: comprovam fluxo, quarentena, isolamento e integridade, mas não comprovam CORS nem validação de assinatura pelo provedor real. Homologar: upload de 20 MiB; assinatura expirada; mudança de checksum ou tamanho; tentativa de sobrescrita; revogação durante upload; scanner indisponível. A URL deve rejeitar adulterações no serviço S3 real.

Quando o transporte estiver resolvido, configurar as mesmas variáveis de armazenamento na API e no worker, testar isolamento do bucket, ClamAV real, arquivo infectado de teste, indisponibilidade do scanner e recuperação de falhas. O worker processa um documento por ciclo para não drenar uma fila inteira antes de voltar aos e-mails; medir capacidade e separar workers se necessário.

## Pendências para operação comercial

- Configurar e validar serviços, domínios, segredos e SMTP reais.
- Homologar upload direto e streaming no ambiente hospedado; provisionar S3 privado/ClamAV.
- Concluir integração financeira e ativação de assinatura.
- Ensaiar restauração de banco e objetos; configurar alertas e responsáveis.
- Validar conteúdo, políticas e condições comerciais com a operação.

Procedimentos de backup, incidente e reversão: [Operação](../../docs/OPERACAO.md). Reverter artefatos compatíveis; não restaurar banco automaticamente durante rollback.
