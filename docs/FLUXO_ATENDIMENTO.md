# Fluxo de atendimento no dashboard

Incremento de 29/09/2026. Operação local; não equivale a homologação de produção.

## Jornada disponível

1. Administrador libera o cliente cadastrado e com e-mail confirmado, informando validade e motivo. A autorização não representa pagamento ou assinatura. Revogar ou expirar impede novos envios e preserva os casos assumidos.
2. Cliente cria rascunho, envia documentos e submete para triagem. Administrador distribui; advogado confere escopo, conflito e informações.
3. Após aceite, advogado descreve etapas contratadas, posição do cliente (autor, réu ou requerente), órgão/processo se conhecidos, e seleciona a procuração verificada que enviou.
4. Cliente baixa, assina conforme orientação, envia e seleciona a versão verificada da procuração. Advogado confere ou solicita correção.
5. Advogado salva a minuta interna e publica a peça após confirmação de revisão. Cliente recebe somente a versão publicada. Eventos preservam snapshots de publicação e dos documentos vinculados.
6. Advogado protocola no sistema externo e registra órgão, número, processo e comprovante verificado. A plataforma não realiza protocolo externo.
7. Prazos, audiências e etapas têm data, resultado e remarcação com motivo. Movimentações são visíveis no histórico. Compromissos vencidos entram na atenção do advogado.
8. Advogado encerra com resultado e confirmação, somente sem compromissos ou complementos abertos. Documentos, peças publicadas e histórico permanecem consultáveis; novas mensagens, uploads e ações jurídicas ficam bloqueados.

## Contratos

- `GET/POST /api/v1/admin/service-access`: lista paginada e concessão/revogação administrativa. POST recebe `email`, `enabled`, `reason` e `expiresAt` quando habilitado.
- `GET /api/v1/cases/{id}/workflow`: estado do trabalho e compromissos; minuta apenas ao responsável.
- `POST /api/v1/cases/{id}/workflow`: `version` e `action`. Ações: START, SIGN, VERIFY, RETURN_MANDATE, DRAFT, PUBLISH, FILE, UPDATE, TASK, RESCHEDULE, COMPLETE, CLOSE. Campos são validados conforme a ação.
- Novos estados: AGUARDANDO_PROCURACAO, EM_PREPARACAO, EM_ACOMPANHAMENTO e ENCERRADO.

Mutações bloqueiam o caso no PostgreSQL, conferem versão, papel e atribuição atual. Transferência revoga imediatamente o acesso do advogado anterior. Administrador continua restrito a metadados, distribuição e liberação; não acessa o trabalho jurídico.

## Operação e limites

Aplicar as migrações Django antes de iniciar a nova versão. Usar armazenamento privado e worker de scanner configurados: documentos em quarentena não podem ser usados como procuração ou comprovante. Não existe aprovação fictícia de assinatura, scanner ou pagamento.

A procuração é preparada e enviada pelo advogado; geração automática a partir de modelos, assinatura eletrônica integrada, exportação integral do dossiê, intimações automáticas e lembretes por e-mail ainda não fazem parte deste incremento. A peça é editada como texto no painel; documentos anexos usam o fluxo privado existente. Prazos são informados pelo responsável, sem cálculo automático de prazo jurídico.

## Verificação

Suíte PostgreSQL: 65 testes aprovados, incluindo quatro testes de concorrência. Build Next.js e verificação de migrações aprovados. Quatro jornadas de navegador aprovadas no Edge (três de acesso/isolamento e a jornada ampliada após ajuste do seletor de teste). Fluxo ampliado validado até encerramento, incluindo cliente em 390px. Capturas sintéticas finais conferidas em desktop e celular. Scanner simulado exclusivamente na fixture E2E; ClamAV real continua pendente de homologação.

Nesta máquina, a porta 55432 foi recusada pelo Windows. O PostgreSQL exclusivo de `.local/postgres` foi iniciado em 55439 e somente as conexões locais em `backend/.env` foram ajustadas. Nenhuma conexão externa foi alterada.
