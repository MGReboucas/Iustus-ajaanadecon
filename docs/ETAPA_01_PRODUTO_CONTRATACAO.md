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
