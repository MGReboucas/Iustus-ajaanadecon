# Workers

`run_operations` executa os e-mails de acesso e atendimento, agenda lembretes e limpa dossiês expirados. `--once` executa um ciclo limitado. Localmente, e-mails são gravados em arquivos sem SMTP externo.

`deliver_identity_mail` e `deliver_case_mail` continuam disponíveis separadamente. Usam lease e retry limitado; a entrega é ao menos uma vez. A fila de identidade apaga o corpo criptografado após envio confirmado. A fila de atendimento revalida acesso e preferência antes do envio e não inclui conteúdo jurídico nos e-mails.

`scan_documents` exige ClamAV real e permanece separado. Não é chamado pelo worker de e-mails. Testes simulados não homologam o serviço externo. Alertas operacionais e tratamento manual das falhas permanentes ainda exigem definição operacional.

[Comandos, configuração e limites](../../docs/OPERACAO_LOCAL.md).
