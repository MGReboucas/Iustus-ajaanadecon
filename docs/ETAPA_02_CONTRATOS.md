# Etapa 2 — Contratos entre site, aplicativo e backend

Iniciada em 07/10/2026. Status: EM ANDAMENTO. Etapa 1 segue com regras comerciais pendentes; avançar nesta etapa não aprova essas pendências nem ativa cobrança recorrente.

## Entrega inicial

- Publicação confirmada: `80cbf26` (mobile), `88e42b0` (contratos de propostas) e `57ebd69` (preço) estão no GitHub. As notas históricas de ausência de push foram superadas.
- Contratos de propostas, paginação e decisões centralizados em `contracts/api.ts`, importados como tipos pelos clientes web e mobile.
- Proposta inclui moeda, autor, datas e identificação de quem decidiu, além dos termos exibidos. Tipos de entrada e retorno são usados nas mutações das duas interfaces.
- Backend validado por testes HTTP que conferem conjunto de campos, moeda, centavos, versão, ausência inicial da decisão e autoria após aceite.
- Guia [API](API.md) atualizado: rotas PagBank antigas retornam 410; identidade mobile não exige CSRF de navegador.

## Próximas entregas e critérios de conclusão

- [x] Unificar DTO de propostas sem dependências de execução compartilhadas.
- [x] Conferir resposta HTTP de propostas com testes.
- [x] Compartilhar contratos de casos, timeline, mensagens e atividades recentes.
- [ ] Estender contratos a documentos, notificações, identidade e associação.
- [x] Corrigir estado histórico das atividades recentes e tipar estados dos casos.
- [ ] Completar padronização dos nomes e rótulos de eventos.
- [ ] Revisar campos de cliente/advogado necessários às telas, preservando autorização.
- [ ] Conferir todos os endpoints documentados e remover descrições obsoletas.
- [ ] Definir validação em tempo de execução nos pontos em que respostas inválidas possam comprometer o fluxo.
- [ ] Completar testes de compatibilidade entre canais e registrar evidências finais.

Os tipos TypeScript não substituem os serializers do Django e não constituem validação de runtime. Não houve mudança de payload ou regra de cobrança neste incremento.

Título sugerido do próximo commit: `refactor(api): share proposal contracts across web and mobile`.

## Evidências do incremento inicial

07/10/2026: TypeScript web e mobile aprovados; lint mobile aprovado; 4 testes mobile e 32 testes backend de propostas/mobile aprovados; `git diff --check` aprovado. Mudança apenas de tipos nos clientes, sem alteração visual ou de dados transmitidos. Contratos ainda não são gerados automaticamente dos serializers. A verificação documental global continua com a pendência preexistente do link para `frontend/.env.example` excluído localmente.

## Segundo incremento — casos, mensagens e histórico

- `contracts/api.ts` agora define `CaseState`, `CaseItem`, `MobileCase`, `CaseEvent`, `Message` e `RecentActivity`, usados pelos clientes web/mobile. Mensagens incluem visibilidade; caso inclui versão, responsável e datas anuláveis. Conteúdo narrativo permanece opcional no tipo administrativo e ausente na resposta administrativa.
- Corrigida a origem de `recentActivity.stateLabel`: usa o estado registrado no evento, e não o estado atual do caso. Vale para o painel web e para o mobile, que compartilham a implementação do resumo.
- Testes HTTP conferem campos de detalhe, timeline e mensagens, ausência de relato no acesso administrativo e preservação do rótulo de uma movimentação antiga após encerramento. Mantido isolamento de outro cliente.
- Verificações: tipos web/mobile, lint mobile sem avisos, 4 testes mobile e 22 testes backend de comunicação/mobile aprovados; diff sem erros de formatação. Sem alteração de banco ou pagamento.
- Incremento local pronto para revisão/commit: `refactor(api): share case contracts and preserve historical state`. Não commitado nem enviado nesta rodada.

Próximo conjunto: documentos, notificações e identidade/associação. Etapa 2 ainda em andamento.
