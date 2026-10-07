# Regras de negócio

> Revisão 1.5 · Base: 16/09/2026 · Arquitetura aprovada; validação operacional pendente.

25 regras. As regras confirmadas indicam evidência no produto atual ou decisão explícita do usuário, conforme a situação registrada; hipóteses e decisões propostas precisam de validação conforme [Decisões](DECISOES.md). Não representam aprovação jurídica do serviço.

## RN-001 — Preço base

Preço ativo no código em 07/10/2026: R$ 699,90 anuais em 10 parcelas de R$ 69,99. Pedidos antigos preservam suas condições. Renovação automática aprovada, mas ainda não implementada; acompanhar docs/ETAPA_01_PRODUTO_CONTRATACAO.md.

**Situação:** Preço implementado; recorrência pendente.

## RN-002 — Confirmação financeira

Acesso contratado só é ativado após confirmação confiável de pagamento pelo provedor; token ou código de transação isolado não basta.

**Situação:** Proposto.

## RN-003 — Parcelamento

Pagamento parcelado de contratação anual não representa assinatura mensal; parcelas e juros devem coincidir com a cotação validada.

**Situação:** Confirmado parcialmente; validar oferta.

## RN-004 — Período anual

Associação anual com renovação automática no mesmo parcelamento e possibilidade de cancelar a próxima renovação antes da cobrança, aprovada em 07/10/2026. Implementação e detalhes de calendário e falha de cobrança pendentes; preservar contratos anteriores sem consentimento recorrente.

**Situação:** Regra aprovada; integração pendente.

## RN-005 — Uso ilimitado

Não impor limite comercial de quantidade de casos na vigência; limites técnicos de arquivo e antiabuso não alteram a promessa de uso.

**Situação:** Confirmado na oferta; validar elegibilidade.

## RN-006 — Expiração e casos existentes

Preservar casos existentes após expiração, conforme confirmação de 07/10/2026. Novas submissões dependem de associação ativa; envio não equivale a aceite. Detalhar estorno e contestação sem encerrar trabalho automaticamente.

**Situação:** Preservação confirmada; detalhes financeiros pendentes.

## RN-007 — Propriedade do caso

Cliente só lê e altera recursos do próprio caso dentro das ações permitidas; cliente não edita histórico nem decisões profissionais.

**Situação:** Proposto.

## RN-008 — Acesso profissional

Advogado só acessa casos atribuídos; triagem exige atribuição prévia por administrador; visão de fila não expõe casos de colegas.

**Situação:** Proposto.

## RN-009 — Responsável único

Cada caso tem no máximo um advogado responsável ativo; troca de responsável e justificativa são auditadas.

**Situação:** Proposto.

## RN-010 — Transições

Mudança de estado obedece matriz do fluxo, pré-condições e controle de versão; recusas e reaberturas exigem motivo.

**Situação:** Proposto.

## RN-011 — Arquivo confiável

Somente versão liberada pela verificação pode ser baixada ou usada como evidência; extensão sozinha não comprova formato.

**Situação:** Proposto.

## RN-012 — Versionamento

Substituição cria nova versão imutável; exclusão operacional é lógica e não elimina retenções justificadas.

**Situação:** Proposto.

## RN-013 — Procuração

Preparação jurídica exige procuração conferida conforme modelo e procedimento aprovados pelo responsável jurídico.

**Situação:** Dependência EXT-02.

## RN-014 — Entrega de defesa

Somente peça revisada e explicitamente publicada é visível ao cliente; o próprio responsável pode revisar no MVP, sem exigir segundo advogado.

**Situação:** Hipótese H-03.

## RN-015 — Protocolo externo

No MVP protocolo é realizado fora da plataforma e registrado manualmente com comprovante; registro não equivale a integração com tribunal.

**Situação:** Hipótese H-04.

## RN-016 — Prazos

Advogado informa e confirma vencimentos; lembrete não substitui controle profissional nem calcula prazo processual automaticamente.

**Situação:** Proposto.

## RN-017 — Separação de conteúdo

Notas internas e minutas não aparecem em telas, exportações, e-mails ou APIs do cliente.

**Situação:** Proposto.

## RN-018 — Notificação

Falha de e-mail não desfaz mudança do caso; tentativa e falha ficam registradas para reenvio.

**Situação:** Proposto.

## RN-019 — Auditoria íntegra

Ações críticas geram eventos persistidos; interface não permite apagar ou editar eventos; retenção segue política aprovada.

**Situação:** Proposto.

## RN-020 — Motivação

Recusa, transferência, cancelamento, bloqueio e reabertura exigem motivo e autor; texto público é separado de justificativa interna.

**Situação:** Proposto.

## RN-021 — Privacidade

Pedidos do titular passam por identidade e análise de retenção; não existe eliminação indiscriminada de arquivos por um clique.

**Situação:** Dependência EXT-02.

## RN-022 — Privilégios

Cadastro público cria apenas cliente; advogado e administrador são provisionados por operação autorizada.

**Situação:** Proposto.

## RN-023 — Pedido imutável

Preço, moeda, plano e cotação ficam vinculados ao pedido; servidor ignora total arbitrário enviado pelo navegador.

**Situação:** Proposto.

## RN-024 — Eventos financeiros

Eventos repetidos e fora de ordem são reconciliados com estado autoritativo; falha de consulta não promove pagamento a pago.

**Situação:** Proposto.

## RN-025 — Abrangência material do serviço

Atender multas de trânsito e direito civil em geral, excluindo apenas família e sucessões do escopo civil; consumo, imobiliário e demais matérias civis permanecem incluídos; exemplos de categorias não formam lista fechada; atuação civil inclui ajuizar, defender, protocolar e acompanhar, com aceite profissional e cobertura financeira por etapa definidos separadamente.

**Situação:** Confirmado pelo usuário.
