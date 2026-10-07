# Contratos de API

> Atualização parcial em 07/10/2026: Django concentra identidade, casos, documentos, atendimento, comunicação e associação. Os contratos abaixo devem distinguir código implementado de propostas históricas. Homologação produtiva é separada de implementação.

## Rotas financeiras atuais e legado

- `GET /api/v1/billing/plan`: oferta atualmente configurada; não confundir com a nova oferta comercial aprovada e ainda não ativada.
- `GET /api/v1/billing/card-key`: chave pública do provedor.
- `POST /api/v1/billing/checkout`: cria/reenvia tentativa de pagamento; `GET` consulta situação na sessão do comprador.
- `POST /api/v1/billing/webhook`: notificação autenticada do provedor, sem autenticação por cookie.
- `POST /api/v1/billing/activate` e `/billing/resend`: ativação e reenvio de acesso.
- As rotas legadas `/api/pagbank/session` e `/api/pagbank/payment` retornam HTTP 410; não constituem outro caminho de cobrança. Detalhes em [Associação](ASSOCIACAO.md).
- `GET /api/v1/health/`: liveness público. `GET /api/v1/ready`: verificação de banco; não certifica filas, e-mail ou demais fornecedores.

## Contratos compartilhados de propostas

A fonte TypeScript consumida pelo site e aplicativo é [contracts/api.ts](../contracts/api.ts). O backend permanece responsável pela validação e autorização; tipos TypeScript não validam respostas em tempo de execução. Testes HTTP conferem os campos emitidos pelo Django, os identificadores de decisão e valores monetários.

| Operação | Web (prefixo `/api/v1`) | Mobile (prefixo `/api/v1/mobile`) |
| --- | --- | --- |
| Consultar | GET `/cases/{caseId}/proposals` | GET `/cases/{caseId}/proposals` |
| Publicar | POST `/cases/{caseId}/proposals`, advogado atribuído | Não exposta |
| Decidir | POST `/cases/{caseId}/proposals/{proposalId}/decision`, titular | Mesmo caminho, titular |

- Lista: `Page<ServiceProposal>` com `results` e `nextCursor`; cursor opaco enviado como `?cursor=...`.
- Publicação: `ProposalInput`; decisão: `ProposalDecisionInput`; retorno de mutação: `ProposalResult` com proposta e versão atual do caso.
- Valores: inteiro em centavos e moeda `BRL`; datas ISO 8601 com fuso; identificadores UUID; campos ausentes de decisão retornam `null`.
- Estados: `OPEN`, `ACCEPTED`, `DECLINED`, `SUPERSEDED`. Expiração deriva de `validUntil`; proposta aberta expirada não pode ser aceita.
- Mutação usa a versão do caso; conflito retorna 409. Repetição da mesma decisão já registrada é idempotente. Nova publicação exige versão atualizada.
- Web usa sessão e CSRF. Mobile usa bearer, sem cookies. O proxy não encaminha bearer para rotas web. APIs mobile não herdam autenticação por sessão web.
- Campos extras são rejeitados. Erros seguem envelope `error` com `code`, `message` e campos quando aplicáveis.
- Consulta respeita titularidade/atribuição; administrador não recebe acesso ao conteúdo das propostas. Nenhuma ação destes endpoints cobra honorários.

Acompanhar expansão dos contratos na [etapa 2](ETAPA_02_CONTRATOS.md).
## Identidade implementada neste incremento

Prefixo /api/v1, sem barra final nas rotas abaixo. As mutações web de identidade exigem CSRF, inclusive anônimas; as rotas mobile usam autenticação bearer própria. Acesso por proxy privado validado; exemplos de HTTP e cookies locais não são configuração de produção. Campos desconhecidos são rejeitados.

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
| GET/PATCH /me | Perfil do próprio usuário; PATCH não implementado |
| GET /dashboard/client | Sessão CLIENT; perfil e caseManagementAvailable=true |
| GET /dashboard/team | Sessão LAWYER/ADMIN com MFA; perfil e caseManagementAvailable=true |

Aceite development-v1 registra somente ciência do ambiente de testes. Políticas jurídicas versionadas do contrato futuro ainda não foram implementadas. Erros atuais usam error.code e error.message; requestId e contrato OpenAPI permanecem pendentes. Veja [Acesso local](ACESSO.md).

## Inventario executavel e propostas anteriores

Consulte [API_ROTAS.md](API_ROTAS.md) para todas as rotas e metodos registrados no Django. O comando de geracao possui modo `--check` para detectar divergencias. Permissoes continuam nos servicos e testes; a existencia de uma rota nao concede acesso.

As tabelas de endpoints futuros foram movidas para [propostas historicas](API_PROPOSTAS_HISTORICAS.md), sem apresenta-las como implementadas. Nao existem atualmente as rotas de cotacao, assinatura recorrente e estorno administrativo propostas naquele arquivo.

Listas de casos usam cursor opaco e pagina de 20 registros. Nao existe parametro geral `limit` publicado. Erros usam `error.code`, `error.message` e `error.fields`; `requestId` nao faz parte do envelope atual.

## Atendimento após triagem

Liberação administrativa e fluxo jurídico: [contratos, estados e permissões](FLUXO_ATENDIMENTO.md).

Modelos de procuração, emissão PDF e exportação privada: [contratos](PROCURACOES_EXPORTACAO.md).

## Casos, timeline e mensagens — contratos compartilhados

`contracts/api.ts` define os tipos consumidos pelos clientes. `CaseItem` representa lista/detalhe, com título e relato omitidos no acesso administrativo; o detalhe mobile acrescenta `canMessage`. Datas sem valor são `null`, versão é inteiro e `lawyerId` pode ser `null`.

Timeline retorna `Page<CaseEvent>` com estado registrado no evento. Mensagens retornam `Page<Message>` e visibilidade `PUBLIC` ou `INTERNAL`; a API filtra conteúdo interno antes de responder ao cliente. Compartilhar o tipo não concede permissão de leitura.

No resumo, `recentActivity.stateLabel` descreve o estado na data do evento; `attentionCases[].stateLabel` descreve o estado atual do caso. Essa distinção é testada para não reescrever o significado de movimentações antigas.

## Documentos, notificações e acesso — tipos compartilhados

O mesmo módulo de contratos contém perfil web e perfil mobile restrito a cliente, contexto CSRF web, associação, capacidade de submissão, resumos do painel, avisos e plano de cobrança. `Membership.expiresAt` é `null` sem associação ativa; `Overview.submission` é `null` para profissionais. O dashboard nativo é exclusivo do cliente.

Upload retorna `uploadId`, `uploadUrl`, `expiresAt`, `directUpload` e `version`. A versão informa autor, arquivo, tamanho, estado e data. Autorização de envio direto descreve URL temporária, método PUT, cabeçalhos e validade em segundos. Esses tipos não tornam o arquivo disponível: a liberação continua dependente da verificação no backend.

Notificações incluem `kind` e `readAt` anulável; não incluem o texto da mensagem privada. O plano retorna valor em centavos, parcelas, versão do plano, disponibilidade, ambiente sandbox e versão de política.
