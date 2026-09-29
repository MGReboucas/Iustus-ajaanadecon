# Dashboard e comunicação

Incremento local de 25/09/2026 para RF-019, RF-020, RF-024 e RF-026. Não representa conclusão integral desses requisitos nem homologação produtiva.

## Experiência disponível

- Cliente: total de casos, distribuição por estado, rascunhos e complementos a enviar, últimas atualizações públicas e central de avisos.
- Advogado: fila atribuída, triagens a realizar, complementos respondidos a conferir, avisos e conversa por caso.
- Administrador: indicadores e fila de distribuição com referência, categoria, estado e responsável; sem relato, mensagens ou notas internas.
- Conversa: mensagens assíncronas persistidas, mais recentes primeiro, paginação e atualização manual. O advogado pode registrar nota interna explicitamente identificada antes e depois do envio.
- Avisos: atribuição ao advogado, início/decisão de triagem, solicitação/resposta/conferência de complemento e novas mensagens públicas. Filtro de não lidos e marcação individual persistida.

Os contadores consideram todo o escopo autorizado, não apenas a primeira página de casos. Próximos passos mostram até cinco casos mais antigos por atualização; a lista completa continua na área de casos. Responder a um complemento retira a pendência do cliente e a coloca na fila de conferência do advogado.

## Contrato implementado

Prefixo `/api/v1`. Sessão, portal e CSRF seguem os controles existentes.

| Rota | Comportamento |
| --- | --- |
| GET `/dashboard/overview` | Contadores, estados, próximos passos, cinco eventos públicos recentes e capacidade de submissão |
| GET `/cases/{id}/summary` | Metadados administrativos; exige ADMIN e exclui rascunhos |
| GET `/cases/{id}/messages?cursor=...` | Até 20 mensagens; cliente recebe apenas PUBLIC, advogado atribuído recebe PUBLIC e INTERNAL |
| POST `/cases/{id}/messages` | `text` de 1 a 10000 caracteres, `visibility` PUBLIC/INTERNAL e UUID `clientMessageId` |
| GET `/notifications?unread=true&cursor=...` | Até 20 avisos próprios, revalidando acesso atual ao caso |
| POST `/notifications/{id}/read` | Corpo `{}`; marcação idempotente, somente do destinatário ainda autorizado |

Mensagem exige caso atribuído, fora de RASCUNHO/RECUSADO. Histórico permanece consultável pelo titular após recusa. Cliente não pode criar notas internas; administrador não acessa conversa. Transferência revoga mensagens, indicadores e avisos do advogado anterior na próxima requisição protegida. O novo responsável pode consultar o histórico público e interno do caso.

Repetir o mesmo `clientMessageId`, autor e caso retorna a mensagem original; alterar texto ou visibilidade com a mesma chave retorna 409. O bloqueio transacional do caso serializa envios concorrentes e transferência. Conteúdo é renderizado como texto, sem interpretar HTML. Auditoria de envio registra identificadores e visibilidade, sem copiar o texto da conversa.

Avisos internos são gravados na mesma transação que o evento ou mensagem, com chave única por origem/destinatário. Falha desfaz a mutação inteira; não há fila ou entrega externa neste incremento. Títulos dos avisos são genéricos e não copiam relatos, mensagens ou motivos administrativos. GET não marca leitura automaticamente.

## Executar e verificar

Com PostgreSQL local ativo, aplicar a migração na raiz:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py migrate
```

Os comandos de inicialização permanecem em [Acesso local](ACESSO.md). Para testes isolados:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py test tests --settings=config.settings.test_postgres --noinput
.\backend\.venv\Scripts\python.exe tests/e2e/fixture.py prepare
npm.cmd run build
$env:PLAYWRIGHT_CHANNEL = 'msedge'
npm.cmd run test:e2e
```

Testes cobrem clientes distintos, dois advogados, administrador, notas internas, transferência, CSRF, validação, paginação, leitura, rollback de avisos e envio simultâneo com a mesma chave. A jornada de navegador inclui conversa, nota interna, texto semelhante a HTML, leitura de avisos e navegação ao caso em celular.

## Limites e próximo incremento

Atualização por botões e após ações locais; sem WebSocket, polling ou promessa de resposta imediata. Avisos começam nos novos eventos, sem recriação retroativa do histórico. Sem anexos na conversa; documentos e anexos de complemento usam o fluxo já existente.

E-mail de novidades do caso e consolidação da outbox com retry continuam pendentes (RF-025/DEV-032/033). A fila de e-mails de identidade existente permanece separada. Assinatura, pagamentos, procuração, prazos e etapas processuais ainda precisam de implementação/integração; o painel não apresenta dados fictícios sobre essas capacidades. Pagamentos e infraestrutura produtiva continuam bloqueadores da entrega comercial.
