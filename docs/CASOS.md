# Casos e triagem — incremento local

> Implementação local de 16/09/2026. Use somente dados fictícios. Não representa liberação comercial, assinatura ativa nem protocolo jurídico.

## Fluxo entregue

1. Cliente cria e edita rascunho, com título, relato e categoria. O rascunho pode estar incompleto.
2. Para enviar, informa título, relato com pelo menos 20 caracteres, categoria e ciência da exclusão de família/sucessões. O servidor exige elegibilidade e chave de idempotência.
3. Administrador recebe fila com referência, categoria, data, estado e responsável. Rascunhos, título e relato não são expostos ao administrador.
4. Administrador atribui advogado ativo, verificado e com MFA confirmado. Motivo administrativo fica no histórico privado.
5. Advogado atribuído inicia triagem, solicita complemento, aceita ou recusa com justificativa publicável.
6. Resposta do cliente mantém o caso aguardando. O advogado confere a resposta e retoma a triagem explicitamente.
7. Aceite exige confirmação de compatibilidade do escopo, análise de conflito e suficiência das informações. Esses itens registram a declaração profissional; o sistema não decide mérito jurídico automaticamente.

Estados implementados: RASCUNHO, SUBMETIDO, EM_TRIAGEM, AGUARDANDO_CLIENTE, ACEITO e RECUSADO. ACEITO encerra somente este incremento de triagem; não significa peça pronta ou processo protocolado. RECUSADO é terminal neste fluxo. Ainda não há reabertura, exclusão, mensagens livres, notificações de casos ou etapas processuais. Desde 21/09/2026, anexos privados e respostas com documentos estão implementados; consulte [Documentos](DOCUMENTOS.md).

Categorias: trânsito, contratos, cobranças, responsabilidade civil, consumo, imobiliário/posse/propriedade e demais matérias civis. A última mantém o escopo civil aberto; família e sucessões não são categorias aceitas. O advogado confirma a classificação durante a triagem. Não há filtragem jurídica automática do texto.

## Como testar

Prepare e inicie frontend, API e PostgreSQL conforme [Acesso local](ACESSO.md). Aplique as migrações na raiz:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py migrate
```

Crie e confirme um cliente fictício com endereço terminado em @example.test. Ele pode salvar rascunhos, mas a submissão fica bloqueada até uma liberação explícita no terminal:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py grant_local_case_access cliente@example.test --days 1 --reason 'Teste fictício de abertura e triagem'
```

O comando exige DEBUG, configuração CASE_LOCAL_TEST_ACCESS e cliente verificado @example.test; aceita de 1 a 7 dias, registra motivo/auditoria e não cria pagamento ou assinatura. Configuração base desabilita essa liberação; settings local a habilita. Após expirar, novos envios são recusados; rascunhos e consultas permanecem disponíveis. Não há botão público de liberação nem endpoint administrativo que permita simular pagamento.

Recarregue o painel do cliente, salve o rascunho e envie. No portal profissional, entre como administrador e distribua o caso. O advogado precisa aceitar seu convite e confirmar MFA antes de aparecer na seleção. Entre com essa conta profissional para triar. Administrador não acumula automaticamente o papel de advogado neste incremento.

## Contrato implementado

Todas as rotas usam /api/v1, sessão válida e CSRF em mutações. Desconhecidos são rejeitados pelos serializers. Cliente e advogado consultam recursos sob propriedade/atribuição; administrador só consulta metadados e altera atribuição.

| Rota | Comportamento |
| --- | --- |
| GET /cases/catalog | Categorias, estados e disponibilidade de envio do próprio cliente |
| GET /cases | Lista no escopo do usuário; state e cursor opcionais; 20 itens por página |
| POST /cases | Cliente cria rascunho; title, description, category, scopeAcknowledged opcionais |
| GET/PATCH /cases/{id} | Detalhe do titular/atribuído; PATCH só em rascunho próprio com version |
| POST /cases/{id}/submit | version e Idempotency-Key de 16–100 caracteres; validação, elegibilidade e envio |
| GET /cases/lawyers | Administrador consulta profissionais elegíveis, com paginação |
| POST /cases/{id}/assignment | Administrador: version, lawyerId e reason; atribuição ou transferência |
| POST /cases/{id}/transitions | Advogado atribuído: version, targetState e reason; aceite exige scopeConfirmed, conflictChecked, informationSufficient |
| GET/POST /cases/{id}/requests | Lista paginada; advogado em triagem cria uma solicitação de complemento textual com version e description |
| POST /cases/{id}/requests/{requestId}/response | Cliente: version e text; uma resposta imutável por solicitação |
| POST /cases/{id}/requests/{requestId}/resolve | Advogado: version e reason; exige resposta e retoma triagem |
| GET /cases/{id}/timeline | Histórico paginado; cliente não recebe eventos administrativos privados |

Listas retornam results e nextCursor. version é inteiro crescente. Alteração concorrente retorna 409 VERSION_CONFLICT; transição incompatível retorna 409 INVALID_TRANSITION. A versão, a alteração e o evento persistem na mesma transação sob lock do caso. Não há endpoint para editar/apagar eventos.

Submissão repetida com a mesma chave e versão original devolve o estado atual sem criar outro envio/evento. Reusar a chave com outra versão retorna 409. Chave não substitui autorização. Alterar o rascunho invalida a versão anterior e exige nova intenção de envio.

Transferência revoga o acesso do advogado anterior na próxima consulta ou mutação, incluindo histórico e complementos. Recursos alheios retornam 404. Paginação e filtros são aplicados depois do escopo. O administrador não recebe relato por detalhe, histórico, lista ou resposta de atribuição.

## Verificação e limites

A suíte completa tem 35 testes Django no PostgreSQL: 22 de fundação/identidade e 13 de casos, incluindo uma disputa real por edição da mesma versão. A jornada de navegador adicional percorre rascunho, bloqueio sem liberação, distribuição, complemento e aceite, com cliente em tela de 390 px. Casos são sintéticos e ficam no banco iustus_e2e; testes Django criam/destroem banco separado. Comandos no [guia de acesso](ACESSO.md).

Pendente: elegibilidade ligada a assinatura autoritativa; homologação do scanner e armazenamento produtivo; checklists por matéria; processos, prazos e procuração; notificações de casos; papéis acumuláveis/concessões excepcionais; políticas, infraestrutura e homologação produtiva. O checkout legado continua sem alteração e sem autorização para cobrança real.
