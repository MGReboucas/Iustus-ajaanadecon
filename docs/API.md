# Contratos de API

> Identidade está implementada e testada localmente conforme a seção abaixo. Casos/triagem possuem contrato local detalhado em [Casos](CASOS.md); pagamentos e demais recursos descrevem o produto futuro. As duas rotas PagBank legadas permanecem no frontend.

## API atual

| Método e rota | Entrada / saída | Limitação encontrada |
| --- | --- | --- |
| GET `/api/pagbank/session` | Sem corpo; retorna `{ id }` ou `{ message }` | Sem identidade de cliente; cria sessão externa; depende de credenciais |
| POST `/api/pagbank/payment` | `cardToken`, `senderHash`, `installment`, `form`; retorna `{ code }` | Recebe campos sensíveis desnecessários, não persiste pedido nem confirma estado financeiro |
| GET `/api/v1/health/` | Público, sem credenciais; retorna `{ "status": "ok" }`, no-store | Somente liveness do processo Django; não verifica PostgreSQL, jobs ou autenticação; ainda sem integração ao frontend |

Migração aprovada: transferir a integração ao módulo billing do backend Django e atualizar o frontend junto, em DEV-012/013/062. Retirar a execução financeira das rotas Next.js antigas; não manter um caminho alternativo de cobrança. O contrato final com PagBank deve corresponder ao produto habilitado em EXT-01; nomes externos de campos, headers e status só serão fixados após DEV-012.

## Identidade implementada neste incremento

Prefixo /api/v1, sem barra final nas rotas abaixo. Todas as mutações exigem CSRF, inclusive anônimas. Acesso por proxy privado validado; exemplos de HTTP e cookies locais não são configuração de produção. Campos desconhecidos são rejeitados.

| Método / rota | Contrato atual |
| --- | --- |
| GET /auth/csrf | csrfToken, portal e policyVersion; não autentica |
| POST /auth/register | name de 2 a 150 caracteres, email, password, policyVersion=development-v1; 202 genérico; portal cliente |
| POST /auth/verify | token de uso único; 204 |
| POST /auth/resend | email; 202 genérico |
| POST /auth/login | email, password; cliente recebe sessão, equipe recebe desafio limitado com 202 |
| POST /auth/mfa/enroll | Desafio da equipe; retorna chave TOTP para cadastro; ainda não autentica |
| POST /auth/mfa/verify | code: TOTP ou código de recuperação; cria sessão; cadastro inicial retorna oito códigos uma única vez |
| POST /auth/recovery | email; 202 genérico |
| POST /auth/reset | token, password; 204 e revogação das sessões/desafios anteriores |
| POST /auth/logout | Encerra sessão; 204 |
| POST /admin/invitations | ADMIN com MFA, corpo somente email; cria convite LAWYER; 202 |
| POST /auth/invitations/accept | token, name, password; cria advogado verificado; 201; login e MFA continuam obrigatórios |
| GET /me | Perfil do próprio usuário; PATCH não implementado |
| GET /dashboard/client | Sessão CLIENT; perfil e caseManagementAvailable=true |
| GET /dashboard/team | Sessão LAWYER/ADMIN com MFA; perfil e caseManagementAvailable=true |

Aceite development-v1 registra somente ciência do ambiente de testes. Políticas jurídicas versionadas do contrato futuro ainda não foram implementadas. Erros atuais usam error.code e error.message; requestId e contrato OpenAPI permanecem pendentes. Veja [Acesso local](ACESSO.md).

## Convenções futuras

Prefixo `/api/v1`, servido pelo Django REST Framework na mesma origem de cada portal por entrada HTTPS controlada; JSON UTF-8. Sessão Django persistida e vinculada ao portal, cookie `__Host-iustus_session` Secure/HttpOnly/Path=/, sem Domain, SameSite=Lax. Não guardar credencial de sessão em localStorage. Listas paginadas por cursor opaco, `limit` padrão 20 e máximo 100. IDs UUID; horários ISO 8601 UTC; valores em centavos.

Usar SessionAuthentication e permissão autenticada por padrão; exceções públicas explícitas. Conforme esse mecanismo do DRF, sessão ausente retorna 403, com código estável `AUTH_REQUIRED`; ação vedada retorna 403 `FORBIDDEN`; falha CSRF retorna 403 `CSRF_FAILED`. Padronizar esses códigos no tratamento de erros, inclusive nas respostas do middleware. Recurso fora do escopo retorna 404; conflito de estado/versão/idempotência 409; validação de serializer 400; regra de negócio inválida 422; limitação 429 com Retry-After; indisponibilidade externa 503. A interface distingue autenticação, permissão e CSRF pelo código, sem ciclo automático de login para todo 403.

Proteção CSRF explícita também em login, cadastro e demais mutações anônimas: obtê-la em GET `/auth/csrf`, enviar `X-CSRFToken` e renovar após login. A proteção de SessionAuthentication sozinha não cobre login anônimo. Webhook financeiro tem exceção CSRF restrita à sua rota e verificação própria do provedor. Respostas privadas e de identidade usam `Cache-Control: no-store`; Next.js não compartilha cache entre usuários. Validar host na entrada e no backend, rejeitando sessão de outro portal mesmo com cookie copiado.

Erro padrão:

```json
{"error":{"code":"INVALID_TRANSITION","message":"O caso foi atualizado. Recarregue antes de continuar.","fields":{}},"requestId":"uuid"}
```

Não retornar stack trace, credenciais, XML bruto do provedor ou detalhes de outro usuário. No servidor, validar objeto por lista explícita de campos; rejeitar campos financeiros proibidos. Corpo JSON limitado inicialmente a 256 KiB; uploads vão para armazenamento privado com limite separado de 20 MiB.

## Identidade e perfil — contrato alvo

| Método / rota | Autorização | Entrada → saída / verificação |
| --- | --- | --- |
| GET `/auth/csrf` | Público, mesma origem | → token CSRF, no-store; não autentica usuário |
| POST `/auth/register` | Público, limitado e com CSRF | name 2–160, email normalizado, senha validada pelo Django, policyVersionIds → 202 genérico; somente papel cliente |
| POST `/auth/verify` | Token temporário | token → 204; uso único e expiração |
| POST `/auth/login` | Público, limitado e com CSRF | email e senha → sessão de cliente ou 202 com desafio MFA temporário para equipe; resposta genérica em falha |
| POST `/auth/mfa/verify` | Desafio temporário, limitado e com CSRF | prova MFA → sessão profissional completa; desafio não autoriza APIs de negócio |
| POST `/auth/logout` | Sessão | → 204 e revogação |
| POST `/auth/recovery` | Público, limitado | email → 202 genérico |
| POST `/auth/reset` | Token temporário | token, nova credencial → 204 e revogação de sessões |
| GET/PATCH `/me` | Próprio usuário | PATCH campos permitidos de perfil → perfil reduzido; e-mail novo exige verificação |
| POST `/admin/invitations` | Admin com MFA | email, role=LAWYER → convite; ADMIN exige concessão reforçada |
| PATCH `/admin/users/{id}` | Admin com MFA | status/roles, reason, version → usuário; impedir último admin removido |

Identidade pertence ao Django; TOTP usa PyOTP e os segredos usam Fernet. O contrato alvo acima inclui capacidades ainda pendentes, como edição de perfil e administração de usuários. Convite da equipe exige cadastro do fator em fluxo limitado, com confirmação antes de conceder sessão profissional. Recuperação/troca de fator exige procedimento reforçado e revogação; não permitir fallback só por senha. Não duplicar credenciais no Next.js.

## Pagamentos e assinatura

| Método / rota | Autorização | Entrada → saída / verificação |
| --- | --- | --- |
| POST `/billing/quotes` | Cliente verificado | planId, contexto mínimo de cotação permitido pelo provedor → quoteId, opções, totais e expiresAt; valor base carregado no servidor |
| POST `/billing/orders` | Cliente verificado | planId, quoteId, installments; header Idempotency-Key → 201 orderId, state e valores imutáveis |
| POST `/billing/orders/{id}/pay` | Proprietário | paymentToken, metadados estritamente exigidos pelo provedor; Idempotency-Key → 202 estado conhecido ou pendente; nunca “pago” por criação apenas |
| GET `/billing/orders/{id}` | Proprietário/admin financeiro | → estado interno, referência e valores mínimos; sem payload integral do provedor |
| GET `/billing/subscription` | Cliente | → state, startsAt, endsAt e permissão para novo caso |
| POST `/billing/webhooks/pagbank` | Provedor verificado | Evento do produto confirmado → 2xx após recebimento durável; repetição reconhecida sem novo efeito |
| POST `/admin/orders/{id}/reconcile` | Admin com MFA | reason → job de consulta ao provedor, 202 |
| POST `/admin/orders/{id}/refund-request` | Admin financeiro com MFA | reason, amountCents permitido → pedido de estorno rastreado; resultado financeiro só muda por confirmação |

**Campos proibidos no backend próprio:** cardNumber/PAN, cvv e expiration. Enviar ao provedor por mecanismo tokenizado homologado. Dados do comprador que o contrato exigir seguem lista explícita, nunca o objeto inteiro do formulário. Chave idempotente é vinculada a usuário, operação e hash do corpo; mesma chave e corpo distinto = 409. Timeout desconhecido impede repetir cobrança sem reconciliação.

## Casos e colaboração — contrato alvo

O incremento implementado usa category (código do catálogo), scopeAcknowledged e liberação de teste; recebe documentos pelo incremento descrito em [Documentos](DOCUMENTOS.md), mas ainda não verifica assinatura real. Rotas, payloads e limites atuais estão em [Casos e triagem](CASOS.md). A tabela abaixo inclui capacidades futuras.

| Método / rota | Autorização | Entrada → saída |
| --- | --- | --- |
| GET/POST `/cases` | Cliente; advogado consulta atribuídos | Filtros permitidos / POST title até 160, description até 20000, categoryId → caso em rascunho |
| GET/PATCH `/cases/{id}` | Proprietário ou atribuído; PATCH conforme estado | Dados permitidos, version → caso; DTO varia por papel |
| POST `/cases/{id}/submit` | Proprietário com vigência | version; Idempotency-Key → caso submetido ou 409/422 |
| POST `/cases/{id}/assignment` | Admin | lawyerId, reason, version → atribuição e nova versão |
| POST `/cases/{id}/transitions` | Advogado atribuído | targetState, reason quando exigido, version → estado e evento |
| GET/POST `/cases/{id}/requests` | Atribuído cria; proprietário consulta | description, tipo, resumeState validado → pendência |
| POST `/cases/{id}/requests/{requestId}/response` | Proprietário | text, documentVersionIds próprios → resposta; não resolve automaticamente |
| POST `/cases/{id}/requests/{requestId}/resolve` | Atribuído | reason, version → pendência resolvida e possível retomada |
| GET/POST `/cases/{id}/messages` | Proprietário/atribuído | text até 10000, visibility; cliente só PUBLIC → mensagem |
| GET `/cases/{id}/timeline` | Proprietário/atribuído | cursor → eventos filtrados por público |
| POST `/cases/{id}/exports` | Proprietário/atribuído | scope permitido → 202 exportId; cliente só conteúdo publicável |
| GET `/exports/{id}/download` | Solicitante autorizado | → URL temporária ou stream; conferir prazo e acesso ao caso |

Filtros não substituem autorização: aplicar escopo antes de paginação e contagem. `caseId` em URL deve coincidir com o documento, mensagem e pendência referenciados no corpo.

## Documentos e gestão jurídica

Upload, conteúdo binário, confirmação, versões e download já possuem implementação local. O contrato exato, incluindo a ausência de `kind` neste incremento e o campo `previousVersion`, está em [Documentos privados](DOCUMENTOS.md). Procurações e peças abaixo continuam propostas.

| Método / rota | Autorização | Entrada → saída |
| --- | --- | --- |
| POST `/cases/{id}/documents/uploads` | Proprietário/atribuído | filename sanitizado, sizeBytes, mime declarado, kind → uploadId e destino privado temporário |
| POST `/uploads/{id}/complete` | Autor com vínculo vigente | checksum declarado → 202; tamanho e hash reais conferidos; quarentena até varredura |
| POST `/documents/{id}/versions` | Autor permitido no caso | Novo upload privado → próxima versão imutável |
| GET `/documents/{id}/versions/{versionId}/download` | Vínculo e visibilidade | → URL de até 5 min; versão AVAILABLE, nunca quarentena |
| POST `/cases/{id}/mandates` | Advogado atribuído | approvedTemplateId, dados validados → geração de PDF versionado |
| POST `/mandates/{id}/signed` | Cliente proprietário | signedDocumentVersionId → SUBMITTED; arquivo do mesmo caso |
| POST `/mandates/{id}/review` | Advogado atribuído | decision, reason, version → APPROVED/REJECTED |
| POST `/cases/{id}/pieces` | Advogado atribuído | documentVersionId → minuta interna |
| POST `/pieces/{id}/review` | Advogado atribuído | documentVersionId, decision → revisão da versão exata |
| POST `/pieces/{id}/publish` | Advogado atribuído | reviewedVersionId, version → entrega e timeline |
| POST `/cases/{id}/protocols` | Advogado atribuído | órgão, referência, data, comprovante → registro manual |
| GET/POST `/cases/{id}/movements` | Atribuído escreve; proprietário consulta público | source, occurredAt, description, visibility → movimento |
| GET/POST `/cases/{id}/deadlines`; PATCH `/deadlines/{deadlineId}` | Atribuído escreve; cliente consulta público | dueDate, timezone, ownerId, source, status e version em alteração → prazo informado |

## Extensão civil confirmada

| Método / rota | Autorização | Entrada → saída |
| --- | --- | --- |
| GET/POST `/cases/{id}/proceedings` | Proprietário consulta versão pública; advogado atribuído escreve | kind, clientPosition, authority, jurisdiction, number opcional → processo; pré-ajuizamento permitido |
| PATCH `/proceedings/{id}` | Advogado atribuído | Campos permitidos e version → processo atualizado; nunca alterar vínculo para caso alheio |
| GET/POST `/proceedings/{id}/parties` | Advogado atribuído; cliente consulta dados necessários à própria atuação | name, role, identifier mínimo → parte protegida |
| GET/POST `/proceedings/{id}/hearings` | Advogado escreve; cliente consulta audiência pertinente ao próprio caso | startsAt, endsAt, timezone, local/link privado, ownerId → audiência e alertas |
| PATCH `/hearings/{id}` | Advogado atribuído | version, alteração ou resultado → evento auditado e invalidação de lembretes antigos |
| GET/POST `/cases/{id}/engagement-stages` | Advogado escreve; cliente consulta escopo próprio | title, included, scopeVersion, ownerId, dueDate → etapa contratada |
| PATCH `/engagement-stages/{id}` | Advogado atribuído | version, status, evidenceVersionId → etapa; fechamento do caso confere pendências |

Links de audiência não aparecem em e-mail ou log; acesso exige vínculo. Remarcação mantém histórico. Tipos de peças incluem petição inicial, defesa e outros atos vinculados à etapa. RF-041 a RF-043 seguem as convenções de validação, minimização e concorrência acima.

## Administração, avisos e privacidade — demais contratos

CRUD de categorias e modelos sob `/admin/categories` e `/admin/mandate-templates`, com inativação/versionamento; GET `/admin/cases` retorna somente metadados para atribuição. POST `/admin/access-grants` exige aprovador distinto do beneficiário, caseId, reason, scope e expiresAt. GET `/admin/audit` exige concessão administrativa e filtros limitados.

GET `/notifications` e PATCH `/notifications/{id}` operam só avisos próprios; GET `/policies/{kind}/current` é público; POST `/me/policy-acceptances` registra versões. POST/GET `/me/privacy-requests` cria/consulta pedidos próprios; PATCH `/admin/privacy-requests/{id}` registra andamento e decisão por operador designado, sem contornar retenções. Catálogos administrativos usam validação, cursor, erros e `version` das convenções gerais.

Transformar estes contratos em serializers DRF e OpenAPI versionado em DEV-059/007; validar compatibilidade com o cliente HTTP TypeScript em CI. Filtrar querysets antes de listagem/contagem e verificar propriedade também na criação; permissão de objeto isolada não cobre essas operações. As rotas `/api/v1/admin` são APIs da aplicação, não o Django Admin. Se habilitado, o Django Admin será restrito à operação e não poderá contornar os serviços, MFA, auditoria e permissões do domínio. Esta versão descreve comportamento e invariantes; schemas externos de fornecedores ainda dependem de validação.
