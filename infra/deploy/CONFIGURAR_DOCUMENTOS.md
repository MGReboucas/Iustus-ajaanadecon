# Configurar armazenamento e antivírus

Este roteiro usa AWS S3 e um Private Service no Render como referência. Os serviços ainda não foram criados ou homologados. Use bucket, contas e dados de homologação separados dos definitivos. Os exemplos não criam recursos automaticamente.

## 1. Bucket AWS S3

No console AWS, abra S3 e crie um bucket de uso geral:

- Nome exclusivo, por exemplo `iustus-homologacao-documentos-SEU-SUFIXO`.
- Região: escolha conforme localização da API e decisão da operação; anote o código para `DOCUMENT_S3_REGION`. O Blueprint atual da API usa Virginia.
- Object Ownership: **Bucket owner enforced**, ACLs desabilitadas.
- Block Public Access: mantenha **os quatro bloqueios ativados**.
- Criptografia padrão: **SSE-S3 (AES256)**, coerente com o código.
- Não habilite hospedagem de site nem acesso público.

A AWS documenta [Object Ownership](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ensure-object-ownership.html) e [bloqueio de acesso público](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html). Criptografia e bucket privado não substituem política de backup/retenção; essa decisão permanece pendente antes de dados reais.

Em Permissions → CORS, aplique [s3-cors.example.json](s3-cors.example.json), trocando os dois endereços pelos portais HTTPS reais. Não use `*`. Cliente e equipe precisam de hosts diferentes, previamente configurados no frontend e no backend.

## 2. Credenciais de serviço

Crie uma identidade IAM exclusiva para a aplicação. Adapte [s3-runtime-policy.example.json](s3-runtime-policy.example.json), substituindo `SUBSTITUA_BUCKET`. O prefixo padrão é `iustus/objects`; altere a política também se mudar `DOCUMENT_S3_PREFIX`.

A permissão de listagem do bucket permite ao backend distinguir objeto ausente de acesso negado; as operações sobre conteúdo ficam limitadas ao prefixo. Não use credenciais root ou permissões de administrador.

A checagem de configuração requer adicionalmente [s3-audit-policy.example.json](s3-audit-policy.example.json). Essa política só lê configuração do bucket e pode ficar restrita à identidade usada na homologação. O runtime não precisa dela para enviar/ler documentos.

Cadastre as chaves diretamente nas variáveis privadas da API e do worker. Não envie valores pelo chat, não coloque em `NEXT_PUBLIC_*` e não versione arquivos preenchidos.

## 3. ClamAV privado no Render

No Render, crie um **Private Service**, no mesmo workspace, região e ambiente de rede da API/worker. Não crie um Web Service público para o scanner. [Serviços privados](https://render.com/docs/private-services) e [rede privada](https://render.com/docs/private-network).

Use a imagem oficial `clamav/clamav`, escolhendo uma versão estável suportada e registrando a versão/digest usada na homologação. A imagem `stable` pode servir para identificar a versão atual; fixe a versão validada antes de produção. Siga a [documentação da imagem](https://docs.clamav.net/manual/Installing/Docker.html).

- Reserve **4 GiB de RAM** como referência da documentação oficial; não reutilize o plano de 512 MB da API.
- Mantenha FreshClam habilitado e aguarde o carregamento/atualização das assinaturas.
- Configure ClamD para ouvir na rede interna, TCP **3310**, com limite INSTREAM de pelo menos **20 MiB**.
- Para persistir assinaturas, monte um disco em `/var/lib/clamav` e use uma imagem `_base` adequada; confira os custos do serviço e do disco no painel.
- Copie o hostname interno pelo painel Render. Ele deve ser apenas o host, sem `http://`, caminho ou porta.
- Não exponha 3310 à internet. O protocolo ClamD usado aqui não fornece autenticação nem TLS; a fronteira é a rede privada.

## 4. Variáveis da API e do worker

Configure os mesmos valores nos dois serviços:

```dotenv
DOCUMENT_STORAGE_BACKEND=s3
DOCUMENT_DIRECT_UPLOAD_ENABLED=false
DOCUMENT_S3_BUCKET=nome-real-do-bucket
DOCUMENT_S3_REGION=regiao-real
DOCUMENT_S3_ENDPOINT=
DOCUMENT_S3_PREFIX=iustus/objects
DOCUMENT_S3_ADDRESSING_STYLE=auto
DOCUMENT_S3_ACCESS_KEY=preencher-no-painel
DOCUMENT_S3_SECRET_KEY=preencher-no-painel
DOCUMENT_SCANNER_HOST=hostname-interno-do-scanner
DOCUMENT_SCANNER_PORT=3310
```

Para AWS S3, deixe o endpoint vazio. Essas variáveis complementam as demais de [production.env.example](production.env.example), incluindo PostgreSQL, segredos, SMTP e origens. O Blueprint atual não provisiona o scanner nem preenche essas variáveis automaticamente.

API e worker de homologação devem estar restritos a avaliadores. `DOCUMENT_STORAGE_BACKEND=s3` já habilita o fluxo de documentos via proxy; o flag de envio direto controla somente o transporte. Não faça essa ativação em ambiente aberto a clientes antes da validação.

## 5. Pré-checagem nos serviços

No Shell da API e depois do worker, com o ambiente configurado:

```sh
python manage.py check_document_services --settings=config.settings.production
```

O comando lê bloqueio público, Object Ownership, política e CORS do bucket. Depois envia duas amostras em memória ao scanner: uma limpa e o padrão de teste inofensivo EICAR. Não grava objetos, não altera configurações, não consulta casos e não imprime credenciais.

Para diagnóstico separado:

```sh
python manage.py check_document_services --only storage --settings=config.settings.production
python manage.py check_document_services --only scanner --settings=config.settings.production
```

Falhas retornam código diferente de zero. O teste EICAR pode gerar um alerta esperado do antivírus; ele não é malware real. O comando foi testado com serviços simulados, ainda não com a sua infraestrutura.

## 6. Homologação no navegador

Após a pré-checagem, ative `DOCUMENT_DIRECT_UPLOAD_ENABLED=true` na API e no worker de homologação. O frontend atualizado recebe a modalidade pela API; nenhuma chave S3 vai para suas variáveis públicas.

Com contas sintéticas nos dois portais:

1. Envie um PDF válido de **20 MiB**. Na rede do navegador, os bytes devem seguir por PUT ao S3; somente JSON passa pelo proxy.
2. Confirme que o estado permanece em quarentena até o scanner liberar.
3. Baixe com o titular e advogado autorizado; tente com outro cliente e confirme a recusa.
4. Valide CORS de ambos os portais e bloqueio de uma origem não configurada.
5. Valide que URL expirada, checksum/tamanho adulterados e tentativa de sobrescrita são recusados pelo S3.
6. Valide revogação de sessão antes da confirmação e indisponibilidade do scanner.
7. Teste downloads e exportações grandes através do streaming hospedado.

A pré-checagem não comprova PUT assinado, IAM completo do runtime, criptografia efetiva dos objetos, atualização/frescura de assinaturas, capacidade ou desempenho. Registre esses resultados antes de liberar documentos reais.

Ao concluir a configuração, informe somente: nome/região do bucket, hostname interno do scanner e os dois endereços dos portais. As chaves ficam no gerenciador de ambiente dos serviços.
