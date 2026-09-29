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

Antes de abrir documentos a clientes, implementar transferência direta autorizada para armazenamento privado (preservando quarentena, integridade e autorização) ou hospedar o proxy em infraestrutura compatível. Validar também downloads e exportações grandes. Não reduzir silenciosamente o limite funcional de 20 MiB.

Quando o transporte estiver resolvido, configurar as mesmas variáveis de armazenamento na API e no worker, testar isolamento do bucket, ClamAV real, arquivo infectado de teste, indisponibilidade do scanner e recuperação de falhas. O worker processa um documento por ciclo para não drenar uma fila inteira antes de voltar aos e-mails; medir capacidade e separar workers se necessário.

## Pendências para operação comercial

- Configurar e validar serviços, domínios, segredos e SMTP reais.
- Resolver transporte de arquivos e provisionar S3 privado/ClamAV.
- Concluir integração financeira e ativação de assinatura.
- Ensaiar restauração de banco e objetos; configurar alertas e responsáveis.
- Validar conteúdo, políticas e condições comerciais com a operação.

Procedimentos de backup, incidente e reversão: [Operação](../../docs/OPERACAO.md). Reverter artefatos compatíveis; não restaurar banco automaticamente durante rollback.
