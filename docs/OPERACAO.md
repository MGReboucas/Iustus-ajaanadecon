# Implantação e operação

> Configuração técnica atual: [roteiro de implantação](../infra/deploy/README.md). Já existem settings de produção, Dockerfile e Blueprint; sua existência não comprova homologação externa.

> Runbook de preparação. Endereços, fornecedores, responsáveis e credenciais serão definidos em EXT-03/06; nenhum deploy foi feito nesta etapa.

## Ambientes

| Ambiente | Dados | Serviços | Permissões |
| --- | --- | --- | --- |
| Desenvolvimento | Sintéticos locais | Sandbox/fixtures | Desenvolvedor, sem credencial produtiva |
| Homologação | Sintéticos controlados | Conta sandbox e infraestrutura separada | Avaliadores convidados e acessos revogáveis |
| Produção | Dados reais após autorização | Serviços contratados e monitorados | Acesso mínimo, MFA e trilha |

Configuração local e comandos atuais: [Acesso local](ACESSO.md). O script infra/setup_local.py gera segredos persistentes privados em backend/.env e frontend/.env.local, sem sobrescrever existentes. DATABASE_URL, chave Fernet, segredo Django e chave privada do proxy são exclusivos do servidor; nunca usam NEXT_PUBLIC_. O legado mantém PAGBANK_EMAIL, PAGBANK_TOKEN e NEXT_PUBLIC_PAGBANK_SANDBOX, com suas limitações de homologação.

## Antes de publicar

A arquitetura aprovada terá três processos: frontend Next.js/Node, API Django/Python e worker Python usando o mesmo código de domínio do backend. Entrada HTTPS encaminha telas ao Next.js e `/api/v1` ao Django em cada portal. Banco e armazenamento ficam privados; sessão é vinculada ao host validado, e a origem Django não aceita acesso direto de clientes externos. Não depender do ciclo de vida de uma requisição web para concluir jobs.

Configuração produtiva futura inclui chave secreta Django, conexão PostgreSQL, hosts permitidos, origens CSRF exatas, cookies seguros, DEBUG desativado e credenciais de objetos/e-mail/scanner. Há settings local, testes PostgreSQL/SQLite e E2E; não há settings produtivos homologados. O worker local grava e-mails em arquivos; SMTP produtivo não está configurado. As chaves financeiras hoje utilizadas pelas rotas Next.js serão exclusivas do backend após a migração; o flag público de sandbox permanece coerente com o ambiente do adaptador. Se Django Admin for habilitado, restringir acesso operacional e MFA sem contornar regras de negócio.

1. Conferir aceite M9, decisões bloqueantes e proprietário operacional.
2. Revisar versões, dependências, segredos, políticas e escopo de acesso.
3. Verificar domínio/TLS, DNS de e-mail, bucket privado, segregação de ambientes e callbacks do produto PagBank confirmado.
4. Fazer backup, ensaiar migração e documentar compatibilidade da versão anterior.
5. Conferir alertas, monitoramento externo, fila de falhas e procedimento de restauração.
6. Preparar janela e plano de reversão, sem abrir tráfego real até decisão operacional.

## Implantação e reversão

Pipeline planejado: instalar dependências Node/Python travadas → lint/tipos/testes de ambos → validar contrato OpenAPI e cliente TypeScript → build dos artefatos → verificar configuração Django de produção → executar migrações Django uma vez com backup e compatibilidade → publicar frontend/API/worker → smoke tests por papel e portal → verificar callbacks e worker → liberar operação. DEV-064 valida os três processos, secrets e reversão coordenada. Health checks públicos não revelam configuração; readiness e acesso às dependências são verificados em rede operacional restrita. Migrações destrutivas exigem etapas separadas e plano específico. Em falha, voltar artefatos compatíveis com contrato e banco; não restaurar banco automaticamente, pois pagamentos/eventos posteriores ao backup precisam ser preservados e reconciliados.

Smoke tests usam conta e dados de teste permitidos no ambiente. Em produção, qualquer transação financeira controlada exige procedimento aprovado pelo titular da conta; não usar cartão real ou cobrar nesta etapa documental.

## Monitoramento proposto

| Sinal | Gatilho inicial a validar | Resposta |
| --- | --- | --- |
| Disponibilidade web | Duas falhas seguidas em check de 5 min | Investigar deploy e dependências |
| Erros HTTP | Taxa 5xx acima de 5% por 5 min com volume relevante | Correlacionar requestIds, pausar release |
| Pagamento indeterminado | Pedido UNKNOWN sem conciliação por 15 min | Consultar provedor; bloquear repetição indevida |
| Worker | Job vencido por 10 min ou fila de falhas não vazia | Reativar consumidor e reprocessar com deduplicação |
| Scanner | Arquivos em quarentena por mais de 15 min | Investigar serviço; manter bloqueio de download |
| Backup | Ausência de cópia bem-sucedida nas últimas 24h | Corrigir e criar nova cópia; investigar integridade |
| Armazenamento/banco | Uso acima de 80% da capacidade contratada | Planejar expansão e revisar retenção autorizada |

Limites são parâmetros iniciais, não garantias. Alertas devem chegar ao responsável operacional designado; uma equipe de plantão não foi presumida. Meta de 99,5% depende de cobertura e fornecedores aprovados, e deve ser revisada se um único desenvolvedor não puder sustentá-la.

## Backup e restauração

Proposta: backup diário do banco, versões/recuperação de objetos e retenção operacional de 30 dias, a aprovar com política de dados. Meta RPO 24h e RTO 8h. Registrar data, integridade, acesso e resultado de cada cópia. Ensaiar restauração antes de produção e a cada mudança relevante; programar ensaio trimestral na operação.

Procedimento: declarar incidente → delimitar ponto de recuperação → restaurar cópias em ambiente isolado → verificar integridade e correspondência de objetos → reaplicar restrições/eliminação decididas → reconciliar eventos financeiros posteriores → validar fluxos → liberar com decisão documentada. Medir perda potencial e duração; se não atingir metas, corrigir ou revisar baseline antes de prometer disponibilidade.

## Incidente

Responsável operacional coordena, desenvolvedor investiga tecnicamente, responsável jurídico/privacidade avalia efeitos sobre titulares e comunicações aplicáveis. Conter acesso, preservar evidências, revogar segredos comprometidos, recuperar, verificar integridade e registrar causa/ações. Não copiar documentos jurídicos para chats ou tickets públicos. Lista nominal de contatos e canais precisa existir antes de M10.

## Rotina após lançamento

Operação assistida está limitada à janela prevista em DEV-054. Manutenção contínua, suporte, novos requisitos e disponibilidade de longo prazo exigem plano de capacidade próprio; não cabem indefinidamente nas horas de implantação. Revisar fila, conciliação, backups, acessos, dependências e solicitações de privacidade em periodicidade aprovada.
