# Demonstração remota gratuita de arquivos

Implementação opt-in para validar envio, listagem, versões e download com arquivos
fictícios. Não equivale à homologação do antivírus nem libera ocorrências reais.
Sem execução local: os testes adicionados são executados pelo CI do GitHub.

## Configuração

1. Criar um projeto no plano Free do Supabase, dedicado à demonstração.
2. Em Storage, criar `iustus-demo` com **Public bucket desativado**. Não criar
   políticas de acesso para anon/authenticated. O backend usa a chave `service_role`
   somente no servidor. Não utilizar a chave anon/publishable.
3. Guardar a URL do projeto e preencher a chave diretamente no Environment do Render.
4. Confirmar o deploy do backend com este código e a migração
   `python manage.py migrate --noinput`. O Blueprint já tem preDeployCommand;
   o serviço Python criado manualmente precisa aplicar a migração no seu fluxo de deploy.
5. Configurar juntas as variáveis abaixo, preservando as demais já existentes:

```dotenv
DOCUMENT_STORAGE_BACKEND=supabase
DOCUMENT_DEMO_ENABLED=true
DOCUMENT_DEMO_EMAILS=EMAIL_DA_CONTA_DE_TESTE
DOCUMENT_DIRECT_UPLOAD_ENABLED=false
DOCUMENT_SUPABASE_URL=https://SEU-PROJETO.supabase.co
DOCUMENT_SUPABASE_BUCKET=iustus-demo
DOCUMENT_SUPABASE_SERVICE_KEY=PREENCHER_SOMENTE_NO_RENDER
```

Nenhuma chave vai ao frontend ou ao GitHub. Outros e-mails, separados por vírgulas,
podem ser autorizados explicitamente. Tanto o usuário quanto o dono da ocorrência
precisam estar na lista; o vínculo normal com o caso continua obrigatório.

## Testar no site publicado

Entrar com a conta autorizada (perfil associado/CLIENT), criar um rascunho e abrir
Documentos do caso. Não é necessário pagar associação para salvar rascunhos.
Enviar PDF, JPEG ou PNG fictício de até **3 MiB**, baixar e comparar, depois enviar
uma nova versão. O limite reduz o corpo trafegado pelo proxy durante esta etapa.
O estado persistido é `DEMO_UNVERIFIED`: nunca `AVAILABLE`, nunca com `scanned_at`.
Não há worker/ClamAV neste fluxo. Anexos de demonstração não contam como documentos
verificados para submissão, complementos ou procurações. Geração/exportação de
documentos está bloqueada neste adaptador.

Os downloads continuam autenticados, com token de curta duração e verificação do
vínculo atual. O servidor confere que o bucket permanece privado antes das operações.
Remover o e-mail da lista ou desligar a demonstração revoga inclusive links emitidos.
O celular ainda não apresenta o botão de download para este novo estado; validar na web.

## Limites e transição

O plano gratuito tem cotas de armazenamento e tráfego; acompanhar no Supabase e
manter poucos arquivos fictícios. Esta alteração não cria recursos nem ativa planos pagos.
Não há limpeza automática nem migração automática de objetos entre provedores.
Antes de trocar de armazenamento, encerrar a demonstração e descartar os objetos
fictícios no bucket dedicado; preservar o estado não verificado dos registros antigos.
Para desativar, definir `DOCUMENT_STORAGE_BACKEND=disabled` e
`DOCUMENT_DEMO_ENABLED=false` juntos. Para operação real, configurar S3, scanner e
worker conforme CONFIGURAR_DOCUMENTOS.md; arquivos demonstrativos não são promovidos.

Referências: https://supabase.com/docs/guides/storage/pricing e
https://supabase.com/docs/guides/storage/security/access-control.
