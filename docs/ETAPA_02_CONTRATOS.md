# Etapa 2 — Contratos entre site, aplicativo e backend

Iniciada em 07/10/2026. Status: EM ANDAMENTO. Etapa 1 segue com regras comerciais pendentes; avançar nesta etapa não aprova essas pendências nem ativa cobrança recorrente.

## Entrega inicial

- Commit anterior `80cbf26`: propostas no aplicativo, criado localmente. Sem novo push.
- Contratos de propostas, paginação e decisões centralizados em `contracts/api.ts`, importados como tipos pelos clientes web e mobile.
- Proposta inclui moeda, autor, datas e identificação de quem decidiu, além dos termos exibidos. Tipos de entrada e retorno são usados nas mutações das duas interfaces.
- Backend validado por testes HTTP que conferem conjunto de campos, moeda, centavos, versão, ausência inicial da decisão e autoria após aceite.
- Guia [API](API.md) atualizado: rotas PagBank antigas retornam 410; identidade mobile não exige CSRF de navegador.

## Próximas entregas e critérios de conclusão

- [x] Unificar DTO de propostas sem dependências de execução compartilhadas.
- [x] Conferir resposta HTTP de propostas com testes.
- [ ] Estender contratos a casos, timeline, documentos, mensagens, notificações, identidade e associação.
- [ ] Padronizar estados/eventos e corrigir descrições históricas inconsistentes.
- [ ] Revisar campos de cliente/advogado necessários às telas, preservando autorização.
- [ ] Conferir todos os endpoints documentados e remover descrições obsoletas.
- [ ] Definir validação em tempo de execução nos pontos em que respostas inválidas possam comprometer o fluxo.
- [ ] Completar testes de compatibilidade entre canais e registrar evidências finais.

Os tipos TypeScript não substituem os serializers do Django e não constituem validação de runtime. Não houve mudança de payload ou regra de cobrança neste incremento.

Título sugerido do próximo commit: `refactor(api): share proposal contracts across web and mobile`.

## Evidências do incremento inicial

07/10/2026: TypeScript web e mobile aprovados; lint mobile aprovado; 4 testes mobile e 32 testes backend de propostas/mobile aprovados; `git diff --check` aprovado. Mudança apenas de tipos nos clientes, sem alteração visual ou de dados transmitidos. Contratos ainda não são gerados automaticamente dos serializers. A verificação documental global continua com a pendência preexistente do link para `frontend/.env.example` excluído localmente.
