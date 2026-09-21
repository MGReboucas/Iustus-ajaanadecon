# Backlog executável

> Revisão 1.5 · Base: 16/09/2026 · Arquitetura aprovada; validação operacional pendente.

64 tarefas, 1360 horas técnicas. Toda tarefa tem prioridade MUST nesta baseline; funcionalidades posteriores estão explicitamente excluídas em [MVP](MVP.md). Os estados distinguem planejamento e incrementos locais; não significam aceite produtivo. Para acesso e casos, consulte também [Estado atual](ESTADO_ATUAL.md). A fase 0 estima a conferência e validação humana, não contabiliza retroativamente o tempo desta sessão.

Arquitetura aprovada: Next.js + TypeScript no frontend, Python + Django REST Framework no backend, PostgreSQL e worker Python separado. DEV-059 a DEV-064 acrescentam 80h técnicas para integração, isolamento dos portais e operação; reserva recalculada por fase. Acesso local possui evidências em [Acesso local](ACESSO.md). Contrato OpenAPI, domínios reais e operação produtiva ainda não foram concluídos.

**Ordem de execução:** a sequência abaixo é estritamente serial, com um desenvolvedor. Dependências técnicas são indicadas por tarefa; a tarefa anterior na lista é também predecessora por capacidade. Cada fase tem reserva separada em [Cronograma](CRONOGRAMA.md). Não executar tarefas automaticamente a partir deste documento: esta entrega é de planejamento; implementação começa após autorização.

**Estimativa:** julgamento de engenharia a partir do inventário e dos critérios abaixo; confiança média-baixa até validar fornecedores e regras. Inclui implementação, testes locais de regra/autorização e revisão de cada entrega. A fase 13 cobre regressão transversal e ensaios; fase 14 cobre aceite e correções esperadas. Contingência cobre desvios não previstos, sem duplicar esses esforços. Reestimar após fase 0 e após homologar pagamento. Espera por terceiros é atraso de calendário, não horas técnicas.

**Definition of Ready:** decisão funcional disponível, contrato e permissão identificados, dados sintéticos e dependências prontas. **Definition of Done:** aceite atendido, testes pertinentes passando, documentação atualizada, revisão de segurança aplicável e evidência vinculada. Sem isso, a tarefa não está concluída.

| ID | Fase | Atividade | Horas | Dependências técnicas | Prioridade |
| --- | --- | --- | --- | --- | --- |
| DEV-001 | 0 | Conferir inventário e riscos do código | 8 | — | MUST |
| DEV-002 | 0 | Validar escopo e regras com responsáveis | 16 | DEV-001 | MUST |
| DEV-003 | 0 | Revisar arquitetura, contratos e planejamento | 16 | DEV-002 | MUST |
| DEV-004 | 1 | Preparar estrutura, configuração e verificação contínua | 16 | DEV-003 | MUST |
| DEV-059 | 1 | Preparar backend Django e contrato DRF | 16 | DEV-004 | MUST |
| DEV-005 | 1 | Criar esquema inicial e migrações Django | 24 | DEV-004, DEV-059 | MUST |
| DEV-006 | 1 | Configurar ambientes e armazenamento privado | 16 | DEV-004 | MUST |
| DEV-060 | 1 | Configurar entrada HTTPS e API por portal | 16 | DEV-006, DEV-059 | MUST |
| DEV-007 | 1 | Criar camada de domínio, erros e autorização | 16 | DEV-005, DEV-006, DEV-060 | MUST |
| DEV-008 | 2 | Implementar cadastro e verificação de e-mail | 24 | DEV-007 | MUST |
| DEV-009 | 2 | Implementar login, logout e sessões Django | 24 | DEV-008 | MUST |
| DEV-061 | 2 | Integrar frontend e sessões isoladas por portal | 16 | DEV-009, DEV-060 | MUST |
| DEV-010 | 2 | Implementar recuperação e alteração de perfil | 16 | DEV-009, DEV-061 | MUST |
| DEV-011 | 2 | Implementar convites, papéis e MFA da equipe | 24 | DEV-009 | MUST |
| DEV-012 | 2A | Validar produto PagBank e contrato de integração | 16 | DEV-011 | MUST |
| DEV-013 | 2A | Corrigir payload e validação financeira do checkout | 24 | DEV-012 | MUST |
| DEV-062 | 2A | Migrar checkout para API Django e retirar rotas legadas | 8 | DEV-013, DEV-061 | MUST |
| DEV-014 | 2A | Persistir pedidos e idempotência de cobrança | 24 | DEV-013, DEV-062 | MUST |
| DEV-015 | 2A | Implementar notificações e conciliação financeira | 32 | DEV-014 | MUST |
| DEV-016 | 2A | Implementar vigência e estados da assinatura | 24 | DEV-015 | MUST |
| DEV-017 | 3 | Implementar rascunho e submissão de caso | 24 | DEV-016 | MUST |
| DEV-055 | 3 | Cadastrar processos, partes e posição do cliente | 24 | DEV-017 | MUST |
| DEV-018 | 3 | Implementar triagem e atribuição | 24 | DEV-017, DEV-055 | MUST |
| DEV-019 | 3 | Implementar máquina de estados e concorrência | 24 | DEV-018 | MUST |
| DEV-020 | 3 | Implementar pendências de documentos e informações | 16 | DEV-019 | MUST |
| DEV-021 | 4 | Implementar upload privado e metadados | 24 | DEV-020, DEV-006 | MUST |
| DEV-022 | 4 | Implementar quarentena e verificação de arquivo | 24 | DEV-021 | MUST |
| DEV-023 | 4 | Implementar versões e download autorizado | 24 | DEV-022 | MUST |
| DEV-024 | 5 | Construir painel e busca do cliente | 24 | DEV-023 | MUST |
| DEV-025 | 5 | Construir detalhe e resposta a pendências | 24 | DEV-024 | MUST |
| DEV-026 | 6 | Construir fila e filtros do advogado | 24 | DEV-025 | MUST |
| DEV-027 | 6 | Construir área de trabalho e triagem | 24 | DEV-026 | MUST |
| DEV-028 | 7 | Implementar modelo versionado e geração de procuração | 24 | DEV-027 | MUST |
| DEV-029 | 7 | Implementar devolução assinada e conferência | 24 | DEV-028 | MUST |
| DEV-030 | 8 | Publicar timeline a partir dos eventos persistidos | 16 | DEV-029, DEV-019 | MUST |
| DEV-031 | 9 | Implementar mensagens e notas internas | 24 | DEV-030 | MUST |
| DEV-032 | 9 | Consolidar outbox e implementar notificações internas | 24 | DEV-031, DEV-022 | MUST |
| DEV-033 | 9 | Implementar e-mails e modelos transacionais | 24 | DEV-032 | MUST |
| DEV-034 | 10 | Implementar peças e revisão para publicação | 32 | DEV-033 | MUST |
| DEV-035 | 10 | Implementar registro de protocolo e movimentações | 24 | DEV-034 | MUST |
| DEV-036 | 10 | Implementar prazos e lembretes | 24 | DEV-035 | MUST |
| DEV-056 | 10 | Implementar agenda de audiências e remarcações | 24 | DEV-036, DEV-055 | MUST |
| DEV-057 | 10 | Implementar etapas contratadas e ciclo judicial | 16 | DEV-056 | MUST |
| DEV-037 | 10 | Implementar encerramento e exportação do caso | 24 | DEV-036, DEV-057 | MUST |
| DEV-038 | 11 | Construir gestão de usuários e atribuições | 24 | DEV-037, DEV-011 | MUST |
| DEV-039 | 11 | Construir gestão de categorias e modelos | 16 | DEV-038 | MUST |
| DEV-040 | 11 | Construir consulta financeira e intervenção controlada | 24 | DEV-039, DEV-016 | MUST |
| DEV-041 | 12 | Consolidar auditoria e revisão de acesso | 24 | DEV-040 | MUST |
| DEV-042 | 12 | Implementar solicitações de privacidade e retenção | 32 | DEV-041 | MUST |
| DEV-043 | 12 | Publicar políticas e revisar comunicação institucional | 16 | DEV-042 | MUST |
| DEV-044 | 12 | Revisar segurança, segredos e minimização | 24 | DEV-043 | MUST |
| DEV-045 | 13 | Executar regressão de regras e isolamento | 24 | DEV-044 | MUST |
| DEV-063 | 13 | Testar fronteiras Next.js, Django e portais | 16 | DEV-045, DEV-061, DEV-062 | MUST |
| DEV-046 | 13 | Executar jornada E2E e testes de falhas externas | 32 | DEV-045, DEV-063 | MUST |
| DEV-058 | 13 | Validar jornadas judiciais como autor e réu | 16 | DEV-046, DEV-057 | MUST |
| DEV-047 | 13 | Verificar desempenho, acessibilidade e navegadores | 24 | DEV-046, DEV-058 | MUST |
| DEV-048 | 13 | Ensaiar restauração e resposta a incidente | 24 | DEV-047 | MUST |
| DEV-049 | 14 | Preparar roteiro e massa para homologação | 16 | DEV-048 | MUST |
| DEV-050 | 14 | Acompanhar homologação funcional e operacional | 24 | DEV-049 | MUST |
| DEV-051 | 14 | Corrigir itens de aceite e fechar homologação | 24 | DEV-050 | MUST |
| DEV-052 | 15 | Preparar produção, alertas e backups | 24 | DEV-051 | MUST |
| DEV-064 | 15 | Validar implantação coordenada de frontend, API e worker | 8 | DEV-052, DEV-063 | MUST |
| DEV-053 | 15 | Executar implantação controlada e reversão ensaiada | 16 | DEV-052, DEV-064 | MUST |
| DEV-054 | 15 | Validar operação assistida e entregar runbook | 16 | DEV-053 | MUST |


## DEV-001 — Conferir inventário e riscos do código

- **Fase:** 0 — Documentação e planejamento.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 8h (1 dias de capacidade).
- **Dependências técnicas:** nenhuma.
- **Predecessora por capacidade:** nenhuma.
- **Requisitos relacionados:** RF-008, RF-009, RNF-003.
- **Descrição e critério de conclusão:** Reproduzir revisão estática, confirmar arquivos e registrar achados com evidência; não executar cobrança.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-002 — Validar escopo e regras com responsáveis

- **Fase:** 0 — Documentação e planejamento.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-001.
- **Predecessora por capacidade:** DEV-001.
- **Requisitos relacionados:** RF-010, RF-012, RF-022, RF-029, RN-004, RN-006, RN-013, RN-015.
- **Descrição e critério de conclusão:** Registrar decisões H-01 a H-06, catálogo de trânsito/civil, fases cobertas e responsabilidade pelo protocolo no escritório com dois advogados; espera externa não conta como hora trabalhada.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-003 — Revisar arquitetura, contratos e planejamento

- **Fase:** 0 — Documentação e planejamento.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-002.
- **Predecessora por capacidade:** DEV-002.
- **Requisitos relacionados:** RNF-001, RNF-009, RNF-013.
- **Descrição e critério de conclusão:** Revisar modelo, permissões, tarefas e calendário; aprovar baseline ou registrar mudanças; concluir M0 somente com revisão.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-004 — Preparar estrutura, configuração e verificação contínua

- **Fase:** 1 — Fundação técnica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-003.
- **Predecessora por capacidade:** DEV-003.
- **Requisitos relacionados:** RNF-013, RNF-014, RNF-016.
- **Descrição e critério de conclusão:** Fixar runtimes Node/Python compatíveis, revisar versões e configurar lint, testes e build em CI para frontend e backend; falha bloqueia entrega.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-059 — Preparar backend Django e contrato DRF

- **Fase:** 1 — Fundação técnica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-004.
- **Predecessora por capacidade:** DEV-004.
- **Requisitos relacionados:** RNF-013, RNF-014, RNF-016.
- **Descrição e critério de conclusão:** Criar base backend, settings separados, dependências travadas, usuário customizado e esquema OpenAPI; comprovar inicialização/testes sem alterar a landing.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-005 — Criar esquema inicial e migrações Django

- **Fase:** 1 — Fundação técnica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-004, DEV-059.
- **Predecessora por capacidade:** DEV-059.
- **Requisitos relacionados:** RNF-006, RF-007, RF-010, RF-011.
- **Descrição e critério de conclusão:** Modelar chaves e índices no Django ORM com usuário customizado definido antes da primeira migração; migrar e restaurar banco de teste sem perda.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-006 — Configurar ambientes e armazenamento privado

- **Fase:** 1 — Fundação técnica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-004.
- **Predecessora por capacidade:** DEV-005.
- **Requisitos relacionados:** RNF-002, RNF-013, RNF-016.
- **Descrição e critério de conclusão:** Provisionar homologação com segredos separados e bucket privado; acesso anônimo negado.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-060 — Configurar entrada HTTPS e API por portal

- **Fase:** 1 — Fundação técnica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-006, DEV-059.
- **Predecessora por capacidade:** DEV-006.
- **Requisitos relacionados:** RNF-001, RNF-002, RNF-013.
- **Descrição e critério de conclusão:** Encaminhar /api/v1 dos portais ao Django e telas ao Next.js; validar hosts, remover headers forjados e impedir acesso direto não confiável à origem.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-007 — Criar camada de domínio, erros e autorização

- **Fase:** 1 — Fundação técnica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-005, DEV-006, DEV-060.
- **Predecessora por capacidade:** DEV-060.
- **Requisitos relacionados:** RNF-001, RNF-012.
- **Descrição e critério de conclusão:** Padronizar serializers DRF, erros, transaction.atomic, eventos/outbox e vínculo; filtrar queryset e validar criação; testes negam consulta cruzada.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-008 — Implementar cadastro e verificação de e-mail

- **Fase:** 2 — Autenticação e usuários.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-007.
- **Predecessora por capacidade:** DEV-007.
- **Requisitos relacionados:** RF-002, RF-037, RN-022.
- **Descrição e critério de conclusão:** Conectar frontend à identidade Django e componente mantido de verificação, incluindo envio mínimo de e-mail; testar duplicidade, aceite e token inválido.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-009 — Implementar login, logout e sessões Django

- **Fase:** 2 — Autenticação e usuários.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-008.
- **Predecessora por capacidade:** DEV-008.
- **Requisitos relacionados:** RF-003, RF-005, RNF-001.
- **Descrição e critério de conclusão:** Criar sessão Django persistida, expiração, rotação e revogação; proteger login por CSRF; testar logout e conta bloqueada.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-061 — Integrar frontend e sessões isoladas por portal

- **Fase:** 2 — Autenticação e usuários.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-009, DEV-060.
- **Predecessora por capacidade:** DEV-009.
- **Requisitos relacionados:** RF-003, RF-005, RNF-001.
- **Descrição e critério de conclusão:** Conectar cliente HTTP TypeScript a sessão Django e CSRF; negar cookie copiado para outro portal, desabilitar cache privado compartilhado e validar renovação do token após login.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-010 — Implementar recuperação e alteração de perfil

- **Fase:** 2 — Autenticação e usuários.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-009, DEV-061.
- **Predecessora por capacidade:** DEV-061.
- **Requisitos relacionados:** RF-004, RF-007.
- **Descrição e critério de conclusão:** Token único e temporário; invalidar sessões e revalidar novo e-mail; testar reutilização.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-011 — Implementar convites, papéis e MFA da equipe

- **Fase:** 2 — Autenticação e usuários.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-009.
- **Predecessora por capacidade:** DEV-010.
- **Requisitos relacionados:** RF-006, RF-033, RN-022.
- **Descrição e critério de conclusão:** Provisionar equipe por convite, exigir MFA privilegiado e impedir autoelevação ou remoção do último administrador.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-012 — Validar produto PagBank e contrato de integração

- **Fase:** 2A — Pagamentos e assinatura.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-011.
- **Predecessora por capacidade:** DEV-011.
- **Requisitos relacionados:** RF-008, RF-009, RN-023, RN-024.
- **Descrição e critério de conclusão:** Confirmar APIs habilitadas e contrato do adaptador Python em sandbox; documentar mapeamento de estados e mecanismo de verificação de eventos.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-013 — Corrigir payload e validação financeira do checkout

- **Fase:** 2A — Pagamentos e assinatura.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-012.
- **Predecessora por capacidade:** DEV-012.
- **Requisitos relacionados:** RF-008, RNF-003, RN-003, RN-023.
- **Descrição e critério de conclusão:** Retirar PAN, CVV e validade do payload interno; validar cotação no servidor; provar com dados sintéticos e inspeção de rede.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-062 — Migrar checkout para API Django e retirar rotas legadas

- **Fase:** 2A — Pagamentos e assinatura.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 8h (1 dias de capacidade).
- **Dependências técnicas:** DEV-013, DEV-061.
- **Predecessora por capacidade:** DEV-013.
- **Requisitos relacionados:** RF-008, RF-009, RNF-003.
- **Descrição e critério de conclusão:** Apontar frontend ao adaptador Django, manter payload mínimo e remover execução financeira das rotas Next.js; testes impedem cobrança por endpoint antigo.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-014 — Persistir pedidos e idempotência de cobrança

- **Fase:** 2A — Pagamentos e assinatura.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-013, DEV-062.
- **Predecessora por capacidade:** DEV-062.
- **Requisitos relacionados:** RF-008, RNF-005, RN-023.
- **Descrição e critério de conclusão:** Criar pedido vinculado ao usuário, chave idempotente e estado indeterminado em timeout; repetição não cria outra cobrança.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-015 — Implementar notificações e conciliação financeira

- **Fase:** 2A — Pagamentos e assinatura.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 32h (4 dias de capacidade).
- **Dependências técnicas:** DEV-014.
- **Predecessora por capacidade:** DEV-014.
- **Requisitos relacionados:** RF-009, RN-002, RN-024, RNF-005.
- **Descrição e critério de conclusão:** Autenticar ou verificar eventos conforme produto confirmado; consultar provedor, tratar repetição e ordem invertida sem ativação indevida.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-016 — Implementar vigência e estados da assinatura

- **Fase:** 2A — Pagamentos e assinatura.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-015.
- **Predecessora por capacidade:** DEV-015.
- **Requisitos relacionados:** RF-010, RF-034, RN-004, RN-006.
- **Descrição e critério de conclusão:** Ativar atomicamente, expirar e reconciliar cancelamento; UI distingue pendente, pago e recusado; testar limites de data.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-017 — Implementar rascunho e submissão de caso

- **Fase:** 3 — Gestão de casos.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-016.
- **Predecessora por capacidade:** DEV-016.
- **Requisitos relacionados:** RF-011, RN-005, RN-007.
- **Descrição e critério de conclusão:** Criar caso próprio com validação e vigência; submissão repetida não duplica e assinatura vencida é recusada.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-055 — Cadastrar processos, partes e posição do cliente

- **Fase:** 3 — Gestão de casos.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-017.
- **Predecessora por capacidade:** DEV-017.
- **Requisitos relacionados:** RF-041, RNF-001.
- **Descrição e critério de conclusão:** Implementar caso civil como autor ou réu, partes privadas, órgão e número opcional antes de ajuizar; testar vínculo após protocolo e acesso cruzado.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-018 — Implementar triagem e atribuição

- **Fase:** 3 — Gestão de casos.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-017, DEV-055.
- **Predecessora por capacidade:** DEV-055.
- **Requisitos relacionados:** RF-012, RF-013, RN-008, RN-009, RN-020, RN-025.
- **Descrição e critério de conclusão:** Designar profissional, aceitar ou recusar com motivo e transferir caso; aplicar exclusão de família/sucessões e permitir demais matérias civis conforme RN-025; testar perda de acesso após transferência.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-019 — Implementar máquina de estados e concorrência

- **Fase:** 3 — Gestão de casos.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-018.
- **Predecessora por capacidade:** DEV-018.
- **Requisitos relacionados:** RF-014, RF-039, RN-010, RNF-006.
- **Descrição e critério de conclusão:** Aplicar matriz e versionamento otimista; conflito não grava histórico parcial; encerramento e reabertura auditados.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-020 — Implementar pendências de documentos e informações

- **Fase:** 3 — Gestão de casos.
- **Prioridade / estado:** MUST / Implementado localmente: complemento com anexos.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-019.
- **Predecessora por capacidade:** DEV-019.
- **Requisitos relacionados:** RF-015, RN-020.
- **Descrição e critério de conclusão:** Criar, responder e resolver pendências; manter retorno ao estado anterior registrado sem permitir saltos inválidos.
- **Evidência:** [Documentos privados](DOCUMENTOS.md): testes locais em 21/09/2026; não representa aceite produtivo.

## DEV-021 — Implementar upload privado e metadados

- **Fase:** 4 — Documentos.
- **Prioridade / estado:** MUST / Implementado localmente; armazenamento produtivo pendente.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-020, DEV-006.
- **Predecessora por capacidade:** DEV-020.
- **Requisitos relacionados:** RF-016, RNF-004, RN-007.
- **Descrição e critério de conclusão:** Validar tamanho e formato, gerar chave privada e vincular arquivo ao caso; rejeitar upload para caso alheio.
- **Evidência:** [Documentos privados](DOCUMENTOS.md): testes locais em 21/09/2026; não representa aceite produtivo.

## DEV-022 — Implementar quarentena e verificação de arquivo

- **Fase:** 4 — Documentos.
- **Prioridade / estado:** MUST / Implementado; homologação do scanner real pendente.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-021.
- **Predecessora por capacidade:** DEV-021.
- **Requisitos relacionados:** RF-016, RNF-004, RNF-018, RN-011.
- **Descrição e critério de conclusão:** Integrar scanner, checksum e worker Python persistente com lease e retry; falhas não liberam download; testar retomada após encerramento do worker e fixture do scanner.
- **Evidência:** [Documentos privados](DOCUMENTOS.md): testes locais em 21/09/2026; não representa aceite produtivo.

## DEV-023 — Implementar versões e download autorizado

- **Fase:** 4 — Documentos.
- **Prioridade / estado:** MUST / Validado localmente; aceite produtivo pendente.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-022.
- **Predecessora por capacidade:** DEV-022.
- **Requisitos relacionados:** RF-017, RF-018, RN-012, RNF-001.
- **Descrição e critério de conclusão:** Preservar versões e emitir URL curta após checagem de vínculo; URL expirada ou arquivo não liberado é recusado.
- **Evidência:** [Documentos privados](DOCUMENTOS.md): testes locais em 21/09/2026; não representa aceite produtivo.

## DEV-024 — Construir painel e busca do cliente

- **Fase:** 5 — Dashboard do cliente.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-023.
- **Predecessora por capacidade:** DEV-023.
- **Requisitos relacionados:** RF-019, RF-038, RNF-008, RNF-015.
- **Descrição e critério de conclusão:** Listar casos, assinatura e pendências com paginação; testar dois clientes, teclado, vazio e erro.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-025 — Construir detalhe e resposta a pendências

- **Fase:** 5 — Dashboard do cliente.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-024.
- **Predecessora por capacidade:** DEV-024.
- **Requisitos relacionados:** RF-011, RF-015, RF-018, RF-019.
- **Descrição e critério de conclusão:** Conectar formulários e documentos no painel; validar jornada abrir caso e enviar complemento em tela pequena.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-026 — Construir fila e filtros do advogado

- **Fase:** 6 — Dashboard do advogado.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-025.
- **Predecessora por capacidade:** DEV-025.
- **Requisitos relacionados:** RF-020, RF-038, RN-008.
- **Descrição e critério de conclusão:** Exibir apenas casos atribuídos e ordenação por vencimento informado; testar filtros sem vazamento.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-027 — Construir área de trabalho e triagem

- **Fase:** 6 — Dashboard do advogado.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-026.
- **Predecessora por capacidade:** DEV-026.
- **Requisitos relacionados:** RF-012, RF-014, RF-020.
- **Descrição e critério de conclusão:** Conectar triagem, documentos e ações permitidas; testar transferência e bloqueio de ações inválidas.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-028 — Implementar modelo versionado e geração de procuração

- **Fase:** 7 — Procurações.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-027.
- **Predecessora por capacidade:** DEV-027.
- **Requisitos relacionados:** RF-021, RF-032, RN-013.
- **Descrição e critério de conclusão:** Gerar PDF com campos validados, armazenar versão do modelo e hash; validar amostra com responsável jurídico.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-029 — Implementar devolução assinada e conferência

- **Fase:** 7 — Procurações.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-028.
- **Predecessora por capacidade:** DEV-028.
- **Requisitos relacionados:** RF-022, RN-013.
- **Descrição e critério de conclusão:** Cliente envia arquivo assinado; advogado aprova ou rejeita com motivo; assinatura externa não é validada automaticamente.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-030 — Publicar timeline a partir dos eventos persistidos

- **Fase:** 8 — Timeline.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-029, DEV-019.
- **Predecessora por capacidade:** DEV-029.
- **Requisitos relacionados:** RF-023, RN-017, RNF-006.
- **Descrição e critério de conclusão:** Expor histórico paginado e filtrado por público; eventos anteriores à tela também aparecem sem duplicar.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-031 — Implementar mensagens e notas internas

- **Fase:** 9 — Comunicação e notificações.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-030.
- **Predecessora por capacidade:** DEV-030.
- **Requisitos relacionados:** RF-026, RN-017.
- **Descrição e critério de conclusão:** Criar conversa por caso e notas restritas; testar API, UI e exportação contra exposição interna e XSS.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-032 — Consolidar outbox e implementar notificações internas

- **Fase:** 9 — Comunicação e notificações.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-031, DEV-022.
- **Predecessora por capacidade:** DEV-031.
- **Requisitos relacionados:** RF-024, RNF-018, RN-018.
- **Descrição e critério de conclusão:** Expandir consumidor existente para avisos com retry e deduplicação; leitura e destinatário respeitam autorização.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-033 — Implementar e-mails e modelos transacionais

- **Fase:** 9 — Comunicação e notificações.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-032.
- **Predecessora por capacidade:** DEV-032.
- **Requisitos relacionados:** RF-025, RNF-003, RN-018.
- **Descrição e critério de conclusão:** Enviar links seguros e genéricos; capturar falhas e bounces; testar duplicação e indisponibilidade do provedor.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-034 — Implementar peças e revisão para publicação

- **Fase:** 10 — Gestão jurídica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 32h (4 dias de capacidade).
- **Dependências técnicas:** DEV-033.
- **Predecessora por capacidade:** DEV-033.
- **Requisitos relacionados:** RF-027, RF-028, RN-014.
- **Descrição e critério de conclusão:** Manter minutas privadas e publicar versão revisada; verificar que cliente nunca consulta minuta.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-035 — Implementar registro de protocolo e movimentações

- **Fase:** 10 — Gestão jurídica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-034.
- **Predecessora por capacidade:** DEV-034.
- **Requisitos relacionados:** RF-029, RF-030, RN-015.
- **Descrição e critério de conclusão:** Registrar fonte, data e comprovante privado; validar campos e separar data do evento da data de registro.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-036 — Implementar prazos e lembretes

- **Fase:** 10 — Gestão jurídica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-035.
- **Predecessora por capacidade:** DEV-035.
- **Requisitos relacionados:** RF-031, RN-016, RNF-018.
- **Descrição e critério de conclusão:** Cadastrar vencimento confirmado, responsável e alertas; editar ou concluir prazo invalida lembretes obsoletos.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-056 — Implementar agenda de audiências e remarcações

- **Fase:** 10 — Gestão jurídica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-036, DEV-055.
- **Predecessora por capacidade:** DEV-036.
- **Requisitos relacionados:** RF-042, RF-031, RNF-018.
- **Descrição e critério de conclusão:** Registrar audiência, responsável, local/link privado e resultado; avisar sobre choque de agenda e invalidar lembrete anterior ao remarcar.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-057 — Implementar etapas contratadas e ciclo judicial

- **Fase:** 10 — Gestão jurídica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-056.
- **Predecessora por capacidade:** DEV-056.
- **Requisitos relacionados:** RF-043, RF-028, RF-029, RF-039.
- **Descrição e critério de conclusão:** Relacionar petição inicial, defesa e demais atos às etapas contratadas; publicação não encerra acompanhamento; impedir fechamento com ato bloqueante ou prazo pendente.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-037 — Implementar encerramento e exportação do caso

- **Fase:** 10 — Gestão jurídica.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-036, DEV-057.
- **Predecessora por capacidade:** DEV-057.
- **Requisitos relacionados:** RF-039, RF-040, RN-006, RN-017.
- **Descrição e critério de conclusão:** Encerrar com motivo e gerar pacote privado com expiração; excluir minutas e notas internas da exportação.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-038 — Construir gestão de usuários e atribuições

- **Fase:** 11 — Administração.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-037, DEV-011.
- **Predecessora por capacidade:** DEV-037.
- **Requisitos relacionados:** RF-013, RF-033, RN-009, RN-022.
- **Descrição e critério de conclusão:** Administração usa serviços Django com MFA, auditoria e concessão por aprovador distinto; testar último administrador, expiração e revogação; restringir Django Admin para não contornar domínio.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-039 — Construir gestão de categorias e modelos

- **Fase:** 11 — Administração.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-038.
- **Predecessora por capacidade:** DEV-038.
- **Requisitos relacionados:** RF-032, RF-021, RN-025.
- **Descrição e critério de conclusão:** Organizar catálogo civil conforme RN-025 sem limitá-lo aos exemplos; família/sucessões fora da oferta; inativar sem quebrar histórico; nova versão de modelo não altera documentos emitidos.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-040 — Construir consulta financeira e intervenção controlada

- **Fase:** 11 — Administração.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-039, DEV-016.
- **Predecessora por capacidade:** DEV-039.
- **Requisitos relacionados:** RF-034, RF-010, RN-024.
- **Descrição e critério de conclusão:** Consultar pedidos, eventos e conciliação; solicitar estorno por fluxo confirmado do provedor; gravar evidência e motivo.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-041 — Consolidar auditoria e revisão de acesso

- **Fase:** 12 — Auditoria, segurança e privacidade.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-040.
- **Predecessora por capacidade:** DEV-040.
- **Requisitos relacionados:** RF-035, RN-019, RNF-001.
- **Descrição e critério de conclusão:** Auditar ações e downloads; limitar consulta administrativa e testar ausência de segredos; revisar todos os endpoints.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-042 — Implementar solicitações de privacidade e retenção

- **Fase:** 12 — Auditoria, segurança e privacidade.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 32h (4 dias de capacidade).
- **Dependências técnicas:** DEV-041.
- **Predecessora por capacidade:** DEV-041.
- **Requisitos relacionados:** RF-036, RN-021, RNF-017.
- **Descrição e critério de conclusão:** Registrar pedido, confirmar identidade, exportar ou eliminar sob política aprovada; testar retenção impeditiva e expiração de exportação.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-043 — Publicar políticas e revisar comunicação institucional

- **Fase:** 12 — Auditoria, segurança e privacidade.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-042.
- **Predecessora por capacidade:** DEV-042.
- **Requisitos relacionados:** RF-001, RF-037, RN-001, RNF-008.
- **Descrição e critério de conclusão:** Publicar textos aprovados e aceite versionado; substituir ou retirar depoimentos fictícios e links vazios.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-044 — Revisar segurança, segredos e minimização

- **Fase:** 12 — Auditoria, segurança e privacidade.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-043.
- **Predecessora por capacidade:** DEV-043.
- **Requisitos relacionados:** RNF-002, RNF-003, RNF-016.
- **Descrição e critério de conclusão:** Revisar ameaças, dependências, cookies, headers e payload; tratar achados e comprovar ausência de cartão em logs.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-045 — Executar regressão de regras e isolamento

- **Fase:** 13 — Testes e estabilização.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-044.
- **Predecessora por capacidade:** DEV-044.
- **Requisitos relacionados:** RNF-001, RNF-005, RNF-006, RNF-014.
- **Descrição e critério de conclusão:** Executar matriz de casos positivos, negativos e concorrentes; registrar resultados e corrigir defeitos conhecidos dentro do escopo.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-063 — Testar fronteiras Next.js, Django e portais

- **Fase:** 13 — Testes e estabilização.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-045, DEV-061, DEV-062.
- **Predecessora por capacidade:** DEV-045.
- **Requisitos relacionados:** RNF-001, RNF-013, RNF-014.
- **Descrição e critério de conclusão:** Validar CSRF no login, header de host forjado, sessão copiada, MFA pendente, cache privado, listagens/criação DRF e tentativas de contornar regras pelo Django Admin.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-046 — Executar jornada E2E e testes de falhas externas

- **Fase:** 13 — Testes e estabilização.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 32h (4 dias de capacidade).
- **Dependências técnicas:** DEV-045, DEV-063.
- **Predecessora por capacidade:** DEV-063.
- **Requisitos relacionados:** RF-008, RF-009, RF-022, RF-028, RNF-012, RNF-018.
- **Descrição e critério de conclusão:** Cobrir contratação até entrega, timeout financeiro, evento repetido, falha de scanner e retry de e-mail com sandbox e fixtures.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-058 — Validar jornadas judiciais como autor e réu

- **Fase:** 13 — Testes e estabilização.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-046, DEV-057.
- **Predecessora por capacidade:** DEV-046.
- **Requisitos relacionados:** RF-041, RF-042, RF-043, RNF-014.
- **Descrição e critério de conclusão:** Testar ajuizamento e defesa, cadastro de protocolo externo, remarcação de audiência, peça posterior e encerramento somente após revisão das pendências.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-047 — Verificar desempenho, acessibilidade e navegadores

- **Fase:** 13 — Testes e estabilização.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-046, DEV-058.
- **Predecessora por capacidade:** DEV-058.
- **Requisitos relacionados:** RNF-007, RNF-008, RNF-015.
- **Descrição e critério de conclusão:** Medir metas com massa sintética e registrar ambiente; corrigir impedimentos nas jornadas principais.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-048 — Ensaiar restauração e resposta a incidente

- **Fase:** 13 — Testes e estabilização.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-047.
- **Predecessora por capacidade:** DEV-047.
- **Requisitos relacionados:** RNF-009, RNF-010, RNF-011, RNF-017.
- **Descrição e critério de conclusão:** Restaurar banco e objetos em isolamento, medir RPO/RTO e simular incidente sem dados reais; registrar evidências.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-049 — Preparar roteiro e massa para homologação

- **Fase:** 14 — Homologação.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-048.
- **Predecessora por capacidade:** DEV-048.
- **Requisitos relacionados:** RNF-014, RF-012, RF-028.
- **Descrição e critério de conclusão:** Criar contas e casos sintéticos para todos os papéis, roteiro e lista de critérios; agendar avaliadores externos.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-050 — Acompanhar homologação funcional e operacional

- **Fase:** 14 — Homologação.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-049.
- **Predecessora por capacidade:** DEV-049.
- **Requisitos relacionados:** RF-010, RF-022, RF-029, RF-036.
- **Descrição e critério de conclusão:** Executar roteiro com responsáveis, registrar aceite ou defeitos; tempo de espera por avaliadores não é hora do programador.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-051 — Corrigir itens de aceite e fechar homologação

- **Fase:** 14 — Homologação.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-050.
- **Predecessora por capacidade:** DEV-050.
- **Requisitos relacionados:** RNF-014, RNF-001.
- **Descrição e critério de conclusão:** Resolver defeitos esperados de aceite e repetir cenários afetados; nenhum bloqueador aberto; obter decisão documentada.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-052 — Preparar produção, alertas e backups

- **Fase:** 15 — Produção.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 24h (3 dias de capacidade).
- **Dependências técnicas:** DEV-051.
- **Predecessora por capacidade:** DEV-051.
- **Requisitos relacionados:** RNF-002, RNF-009, RNF-010, RNF-011, RNF-013, RNF-016.
- **Descrição e critério de conclusão:** Configurar produção isolada, segredos, domínio, monitoração e backups; verificar restauração e contatos operacionais.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-064 — Validar implantação coordenada de frontend, API e worker

- **Fase:** 15 — Produção.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 8h (1 dias de capacidade).
- **Dependências técnicas:** DEV-052, DEV-063.
- **Predecessora por capacidade:** DEV-052.
- **Requisitos relacionados:** RNF-011, RNF-013, RNF-016.
- **Descrição e critério de conclusão:** Conferir artefatos e health checks de três processos, migração única Django, segredos somente no backend e compatibilidade para reversão coordenada.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-053 — Executar implantação controlada e reversão ensaiada

- **Fase:** 15 — Produção.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-052, DEV-064.
- **Predecessora por capacidade:** DEV-064.
- **Requisitos relacionados:** RNF-014, RNF-012.
- **Descrição e critério de conclusão:** Migrar com cópia de segurança, implantar e executar smoke tests; demonstrar reversão compatível sem repetir cobranças.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.

## DEV-054 — Validar operação assistida e entregar runbook

- **Fase:** 15 — Produção.
- **Prioridade / estado:** MUST / Planejado.
- **Estimativa:** 16h (2 dias de capacidade).
- **Dependências técnicas:** DEV-053.
- **Predecessora por capacidade:** DEV-053.
- **Requisitos relacionados:** RNF-010, RNF-011, RNF-018.
- **Descrição e critério de conclusão:** Acompanhar fila, conciliação e alertas durante janela assistida; registrar responsável pela continuidade e pendências sem bloqueadores.
- **Evidência:** demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução.
