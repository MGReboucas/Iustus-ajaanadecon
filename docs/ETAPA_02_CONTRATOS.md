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
- [x] Compartilhar tipos usados nas telas de documentos, notificações, identidade e associação (tipos não substituem validação em execução).
- [x] Corrigir estado histórico das atividades recentes e tipar estados dos casos.
- [x] Completar padronização dos nomes e rótulos de eventos.
- [ ] Revisar campos de cliente/advogado necessários às telas, preservando autorização.
- [x] Conferir todos os endpoints documentados e remover descrições obsoletas.
- [x] Definir validação em tempo de execução nos pontos em que respostas inválidas possam comprometer o fluxo.
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

## Terceiro incremento — documentos, identidade e associação

- `b156f22`, com contratos de casos e correção do estado histórico, publicado na main.
- Centralizados `Profile`, `ClientProfile`, `AuthContext`, `Membership`, `SubmissionAccess`, `Overview`, `MobileDashboard`, `Notice`, `DocumentVersion`, `DocumentUpload`, `DirectUpload` e `BillingPlan`.
- Web consome esses tipos em autenticação, documentos, painel e checkout. Mobile reutiliza perfil de cliente e dashboard, sem ampliar permissão de login de profissionais.
- Incluído `expiresAt` no contrato de upload: o backend já o retornava e o tipo anterior não o descrevia.
- Testes HTTP verificam upload/listagem, perfil, associação inativa e notificações sem narrativa do caso. Respostas administrativas e profissionais continuam sujeitas à autorização do backend.
- Validações: 37 testes backend de documentos/mobile/comunicação; 10 testes frontend de documentos/proxy; TypeScript web/mobile, lint mobile e 4 testes mobile aprovados.
- Sem alteração de banco, preço ou fluxo de cobrança. Novo conjunto será commitado e enviado automaticamente após revisão, conforme autorização do usuário.

Restam revisão integral de rotas documentadas, nomes/rótulos de eventos, validações em execução e testes de compatibilidade complementares. A etapa 2 ainda não está encerrada.

## Quarto incremento — eventos, validação em execução e inventário

- `283cf0f` publicado: contratos de documentos, notificações, identidade e associação.
- Rótulos centralizados em `contracts/events.json`, usados nos históricos web/mobile e no resumo web; incluídos eventos reais de documentos e procuração. Eventos desconhecidos preservam mensagem genérica para compatibilidade.
- `contracts/validation.ts` valida o plano antes de preparar pagamento e a resposta de login antes de persistir sessão mobile. Oferta inválida bloqueia o formulário; sessão malformada, expirada ou de profissional não é persistida no app. Não substitui autorização no servidor.
- `export_api_routes` gera `API_ROTAS.md` do roteamento Django e possui `--check`; conferência adicionada à CI. As tabelas de endpoints propostos foram preservadas em `API_PROPOSTAS_HISTORICAS.md`, explicitamente separadas da API atual.
- Testes dos validadores adicionados à CI. A configuração Metro inclui apenas a pasta de contratos sem dependências, pois este repositório mantém lockfiles separados e não usa npm workspaces.
- Validações locais: tipos web/mobile e testes mobile; 2 testes de validadores; inventário conferido; 3 testes UI mobile e exportações Android/iOS/web aprovados. Checkout inclui regressão de resposta inválida, além dos cenários existentes.
- A validação em execução foi priorizada para oferta e criação de sessão; demais respostas ainda dependem de tipos estáticos, tratamento de erro e verificações do backend. Não afirmar cobertura universal de payloads.

Restam a revisão final dos campos necessários de cliente/advogado e a consolidação das evidências de compatibilidade para encerrar a etapa. Nenhuma mudança de pagamento real, migração de banco ou deploy produtivo neste incremento.
