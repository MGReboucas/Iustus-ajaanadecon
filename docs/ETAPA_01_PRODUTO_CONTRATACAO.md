# Etapa 1 — Produto e contratação

Atualização: 07/10/2026. Status: EM ANDAMENTO. Autorizado iniciar o desenvolvimento; decisões comerciais pendentes ainda não estão aprovadas.

## Referência e objetivo

Consolidar regras para site, aplicativo e backend Django. Complementa [regras do serviço](REGRAS_DO_SERVICO.md), [decisões](DECISOES.md) e [associação](ASSOCIACAO.md). Não é o contrato publicado.

## Decisões anteriores preservadas

- Multas de trânsito e direito civil em geral; exclusões civis: família e sucessões.
- Escritório próprio sediado no RN, dois advogados inicialmente e atuação civil completa: ajuizar, defender, protocolar e acompanhar.
- Cobertura financeira de atos, recursos e despesas e abrangência territorial ainda precisam de definição.
- Django compartilhado pelo site e aplicativo, identidade centralizada e portal profissional separado.

## Decisões confirmadas em 07/10/2026

- Preço: R$ 699,90 por ano, em 10 parcelas de R$ 69,99.
- Renovação automática anual no mesmo parcelamento, permitindo cancelar a próxima renovação antes da cobrança.
- Preservar os casos existentes após expiração ou cancelamento da próxima renovação.
- Assinatura remunera a utilização dos recursos da plataforma; custas, audiências e outras despesas são cobradas separadamente. Honorários por análise, elaboração de peças, protocolo e acompanhamento são definidos separadamente por caso, conforme confirmação do usuário.
- Conta recebedora PagBank é PJ; liberação de recorrência ainda precisa ser verificada pelo titular.
- Não converter contratos anteriores sem renovação automática em autorizações de débito recorrente.

## Implementação atual, distinta da nova oferta aprovada

- Código e oferta atual: R$ 958,80 em 12 parcelas de R$ 79,90.
- Confirmação pelo provedor concede associação anual; nova compra estende o período existente. Fonte: `backend/apps/billing/services.py`.
- Checkout informa ausência de renovação automática. Fonte: `frontend/src/components/AssociationCheckout.tsx`.
- Submissão exige associação ativa; consulta de casos existentes usa titularidade/atribuição. Fontes: `backend/apps/cases/services.py` e `backend/apps/cases/views.py`.
- Cliente acessa seus casos; advogado acessa os atribuídos; administrador tem acesso administrativo restrito.
- Notas e minutas possuem separação; tarefas ainda precisam de visibilidade explícita conforme auditoria.

## Decisões pendentes

| ID | Tema | Decisão necessária |
| --- | --- | --- |
| E1-01 | Preço | Confirmado: R$ 699,90 por ano, em 10 × R$ 69,99. |
| E1-02 | Vigência | Anual com renovação automática no mesmo parcelamento e cancelamento da próxima renovação confirmado. Detalhar calendário, aviso e falhas de cobrança. |
| E1-03 | Expiração | Preservação dos casos confirmada. Novas submissões dependem de associação ativa; envio continua sujeito à triagem. |
| E1-04 | Cobertura | Confirmado: assinatura para utilização dos recursos; custas, audiências e demais despesas à parte. Honorários por análise, peças, protocolo e acompanhamento também são definidos separadamente por caso (confirmado). |
| E1-05 | Público e território | Definir pessoa física/jurídica, terceiros/menores, território e atuação presencial. |
| E1-06 | Cancelamento | Definir canal, procedimento, tratamento financeiro e continuidade dos casos; sem encerramento jurídico automático por evento financeiro. |
| E1-07 | Atendimento | Definir horário, prazo de triagem e canal de urgência. |
| E1-08 | Prestador e termos | Identificação do prestador e responsável pela aprovação dos textos e cobertura. |

Preço, renovação automática e preservação confirmados pelo usuário. Conta PJ confirmada; habilitação da recorrência pendente. Custas, audiências, despesas e honorários jurídicos separados da assinatura confirmados; detalhar contratação individual e demais regras operacionais.

## Regras técnicas

- Backend determina valores e permissões e confirma pagamentos no provedor.
- Nova oferta exige versionamento e preservação das condições dos pedidos anteriores.
- Aceite deve registrar a versão efetivamente apresentada ao comprador.
- Repetição de pagamento do mesmo pedido não duplica associação.
- Envio, atribuição e aceite profissional são eventos distintos.
- Expiração e estorno não apagam histórico nem encerram automaticamente trabalho assumido.
- Conteúdo interno não aparece em consultas, exportações ou avisos ao cliente.

## Entregas e commits

1. Consolidar especificação e corrigir preço documental antigo, sem alterar cobrança.
2. Incorporar respostas e sincronizar regras, decisões e planejamento gerado.
3. Implementar oferta versionada, exibição e validações preservando pedidos antigos. Homologação financeira completa pertence à etapa 4.
4. Verificar consistência entre telas, termos e backend e registrar evidências.

Avisar a cada conjunto pronto para commit com título sugerido e verificações. Atualizar a documentação junto das entregas. Avisar separadamente quando toda a etapa estiver concluída.

## Critérios de encerramento

- [ ] Decisões E1-01 a E1-08 registradas sem aprovação presumida.
- [ ] Oferta consistente nas interfaces aplicáveis e backend.
- [ ] Condições de pedidos antigos preservadas.
- [ ] Vigência, acesso e cancelamento com critérios verificáveis.
- [ ] Documentação sincronizada e verificações aprovadas.
- [ ] Commits e evidências registrados.

## Progresso

07/10/2026: especificação inicial e perguntas comerciais enviadas. Sem alteração de cobrança ou novo commit. Verificação documental integral encontrou link quebrado para `frontend/.env.example`, cuja exclusão já existia antes desta etapa. Etapa não concluída.

## Preparação técnica da nova oferta

`Order` passa a guardar `installments` e `plan_version`, além do valor e da versão da política já existentes. A migração atribui 12 parcelas e `annual-legacy-v1` aos pedidos anteriores. Criação, reenvio e conciliação usam as condições do pedido. Os padrões de cobrança e as telas continuam na oferta antiga neste incremento; a nova oferta não foi liberada como compra recorrente.

Próximo incremento: vincular o aceite à oferta apresentada, implementar o ciclo recorrente e seu cancelamento, atualizar interfaces e liberar a nova oferta somente com esses componentes coerentes. Testar falha e duplicidade de renovação, cancelamento simultâneo e preservação dos casos. Dez parcelas de uma compra anual não equivalem a dez cobranças mensais independentes.

A [documentação de recorrência do PagBank](https://developer.pagbank.com.br/docs/pagamentos-recorrentes), consultada em 07/10/2026, exige conta recebedora PJ aprovada e liberação para integração produtiva. Confirmar também suporte ao parcelamento em cada ciclo anual; não presumir que suporte à recorrência comprova suporte a essa combinação. O adaptador atual usa Orders e não cria assinaturas recorrentes.

Unidade de commit proposta: `feat(billing): snapshot order terms before annual plan migration`. Inclui regras confirmadas, migração e regressões de preservação de pedidos. Não equivale ao encerramento da etapa 1.

### Verificações deste incremento

- 42 testes aprovados: `test_card_checkout` e `test_association`, com banco temporário SQLite e provedor simulado.
- Cenários novos: tentativa antiga após mudança de oferta mantém condições; novo pedido usa 69990 centavos e 10 parcelas; divergência de parcelas não ativa associação; conciliação não depende da configuração atual.
- `makemigrations --check --dry-run`: nenhuma migração faltando.
- `gerar.cjs --check` e `git diff --check`: aprovados.
- Verificação documental integral continua com a pendência preexistente do link para `frontend/.env.example` excluído localmente. Não incluí essa exclusão na entrega.
- Migração gerada e executada pelos testes; não aplicada a banco de produção. Recorrência não implementada/homologada neste incremento.

### Contratação individual do atendimento — regra confirmada

A associação anual remunera o acesso aos recursos da plataforma. Honorários por análise, elaboração de peças, protocolo e acompanhamento são definidos separadamente por caso. Custas, audiências e demais despesas também não estão incluídas na assinatura. A confirmação da atuação civil completa delimita a capacidade de atuação do escritório, não a inclusão financeira desses serviços na assinatura.

Impacto no desenvolvimento: distinguir associação ativa, envio de solicitação, enquadramento profissional e contratação do serviço jurídico. A assinatura ou o simples envio do caso não representam aceite de honorários ainda não apresentados.

Fluxo técnico proposto para detalhamento: registrar proposta individual versionada com escopo, honorários, despesas, condições de pagamento e validade; apresentar ao cliente; registrar aceite ou recusa; preservar versões e comprovantes. Vincular o início das etapas contratadas ao aceite aplicável. Definir com o produto se e quando será exigido pagamento antecipado e se o recebimento ocorrerá na plataforma ou externamente. Não presumir triagem remunerada ou gratuita sem definir o limite entre triagem inicial e análise jurídica contratada.

Atualizar o fluxo de atendimento das etapas 8 e 9 e as telas web/mobile para incluir proposta e aceite individual. A cobrança anual não deve gerar automaticamente uma cobrança de honorários. Implementação de propostas individuais ainda pendente.

### Publicação e próximo incremento — 07/10/2026

- Commit `dd48bec` publicado na branch `main`: preservação das condições dos pedidos e regras comerciais confirmadas. Repositório: https://github.com/MGReboucas/Iustus-ajaanadecon.
- Base de propostas individuais implementada localmente em `apps/legal/proposals.py`, com modelo `ServiceProposal` e migração própria: escopo, honorários em centavos, despesas, condições de pagamento, validade, autor, versão e decisão do titular.
- Publicação serializada pelo bloqueio do caso e controle de versão. Nova proposta substitui apenas a aberta; propostas aceitas preservam seus termos. Aceite/recusa registra ator e data e gera evento no caso. Repetição da mesma decisão não duplica o evento. Proposta expirada ou substituída não pode ser aceita.
- Consulta e decisão limitadas aos participantes autorizados; somente advogado atribuído publica e somente cliente titular decide. A base permite propostas em diferentes fases, sem impor ainda uma política de triagem remunerada.
- 23 testes aprovados (`test_proposals` e `test_workflow`) em SQLite temporário. Concorrência real em PostgreSQL ainda não homologada.
- Este segundo incremento ainda não possui endpoints ou telas; não inicia trabalho jurídico nem cobrança. Propostas complementares ainda exigem definição da relação entre seus escopos. Não substitui contrato publicado ou aceite do novo plano anual.
- Próximas entregas: contratos HTTP, telas profissionais e do cliente, notificações, integração das pré-condições de atendimento e modalidade de pagamento confirmada pelo usuário. Perguntas sobre triagem e pagamento enviadas; respostas pendentes.
- Título sugerido para o segundo commit: `feat(legal): add versioned service proposal domain`. Ainda não enviado ao GitHub.

### API de propostas — incremento seguinte

Commit local `8d45c10`: base de propostas versionadas. O usuário autorizou o commit; não houve novo push neste turno.

Endpoints implementados para sessão web com CSRF nas mutações:

- `GET /api/v1/cases/{caseId}/proposals`: lista paginada com `results` e `nextCursor`. Cada proposta contém identificação, número, escopo, honorários em centavos BRL, despesas, condições de pagamento, validade, estado, autor e decisão.
- `POST /api/v1/cases/{caseId}/proposals`: advogado atribuído envia `version`, `scope`, `feeCents`, `expenses`, `paymentTerms`, `validUntil`. Retorna 201 com `proposal` e a nova `version` do caso.
- `POST /api/v1/cases/{caseId}/proposals/{proposalId}/decision`: titular envia `version` e `accepted`; retorna `proposal` e `version`. Repetição da mesma decisão retorna sucesso sem novo evento. Decisão conflitante, expirada ou substituída é rejeitada.

Campos desconhecidos são rejeitados; respostas não incluem dados de cartão. Consulta respeita titularidade/atribuição, administrador não recebe acesso ao conteúdo. Mutação mantém limite de requisições e controle transacional existentes. A versão do caso pode ser obtida no detalhe do caso antes da ação. A API não cobra honorários e não muda automaticamente a fase jurídica.

Verificação: 19 testes aprovados no módulo `test_proposals` (inclui testes importados da infraestrutura existente); 7 testes do proxy aprovados. Novos cenários HTTP cobrem publicação, consulta, aceite repetido, CSRF, perfil, campos extras e proposta de outro caso. Testes de domínio anteriores cobrem isolamento entre clientes e advogados. Acesso nativo mobile e telas ainda pendentes.

Próximo incremento: telas de proposta e decisão no portal web; notificações e integração ao fluxo após definição sobre triagem e pagamento. Regras pendentes não foram presumidas. Título sugerido: `feat(legal): expose authenticated proposal API`.

### Interface web e avisos de propostas — 07/10/2026

- Commit local `d6e234f` criado: API autenticada de propostas. Não houve push neste turno.
- Tela do caso agora inclui propostas para cliente e advogado: histórico paginado, honorários em reais, escopo, despesas, condições de pagamento, validade e decisão.
- Advogado apresenta nova versão pelo formulário; cliente confirma leitura antes do aceite ou pode recusar. Valores são convertidos para centavos sem usar arredondamento de ponto flutuante. Ações indisponíveis em casos encerrados/recusados e decisões indisponíveis em propostas expiradas.
- Falha de publicação preserva formulário; botões bloqueiam envios simultâneos. Após sucesso, caso e histórico são recarregados. Conflitos de versão continuam decididos pelo backend. Não há cobrança disparada pelo formulário.
- Publicação notifica o titular; aceite e recusa notificam o advogado atribuído. Avisos usam a fila existente, sem valor ou conteúdo da proposta no título. Histórico e visão geral receberam rótulos em português.
- Verificações: TypeScript aprovado; 2 testes de navegador Edge com API simulada (publicação e aceite) aprovados; 26 testes backend de propostas/comunicação aprovados, incluindo destinatários e não duplicação dos avisos.
- Testes de navegador: `npm --prefix frontend exec -- playwright test --config frontend/playwright.proposals.config.ts`.
- Limites: sem homologação de SMTP, pagamento ou concorrência em PostgreSQL; sem tela nativa mobile; ainda não vinculado ao bloqueio de início de trabalho jurídico. Triagem remunerada/gratuita, recebimento e eventual pagamento antecipado aguardam regra comercial.
- Unidade de commit pronta: `feat(web): add case proposals and decision notifications`. Alterações locais ainda não commitadas.

Próxima integração: definir as pré-condições de contratação e início do atendimento e expor a consulta/decisão no aplicativo. Etapa 1 permanece em andamento.

### Propostas no aplicativo — 07/10/2026

- Commit local `7efb5eb`: telas web de propostas e avisos. Não houve novo push neste turno.
- Aplicativo agora consulta propostas paginadas e permite ao titular confirmar leitura, aceitar ou recusar. Exibe escopo, honorários, despesas, pagamento, validade e decisão. Histórico recebeu rótulos de proposta.
- Novas rotas nativas: `GET mobile/cases/{id}/proposals` e `POST mobile/cases/{id}/proposals/{proposalId}/decision`. Reutilizam regras do serviço web, com bearer e sem cookies. Publicação de proposta não é exposta ao cliente mobile.
- Detalhe do caso tipado com versão para controle de concorrência. Atualização manual recarrega proposta e versão; decisões preservam a idempotência do backend.
- Verificações: 32 testes backend; 7 testes do proxy; tipos, lint e 4 testes mobile; 3 testes UI em Edge/viewport móvel com API simulada, incluindo confirmação de leitura e aceite; exportações Android, iOS e web aprovadas.
- Não houve teste em aparelho físico, assinatura de build, cobrança, deploy ou envio ao GitHub deste incremento.
- Próximo commit sugerido: `feat(mobile): add service proposal review and decisions`.
- Etapa 1 permanece aberta pelas regras de triagem, pagamento de honorários e demais condições operacionais, além da implementação/homologação da renovação automática. A decisão de proposta não inicia automaticamente cobrança ou atendimento.
