# communication

Mensagens por caso, notas internas e notificações persistidas, com APIs e testes de autorização e concorrência.

O resumo do dashboard aplica o mesmo escopo de casos do domínio. Notificações e a fila CaseEmail são gravadas na mesma transação da movimentação, com deduplicação por evento e destinatário. Notas internas não geram aviso ao cliente. [Contrato e limites](../../../docs/DASHBOARD_COMUNICACAO.md).

## Destinatários dos e-mails

Avisos `DOCUMENT_*` não são criados na Central de avisos. Os antigos são excluídos da listagem, da contagem de não lidos e da marcação de leitura. O histórico técnico dos documentos permanece na linha do tempo do caso.

| Movimentação | Destinatário |
| --- | --- |
| Rascunhos e processamento/verificação de documentos | Sem e-mail |
| Submissão | Cliente, com relato, categoria, data e referência |
| Atribuição ou troca de advogado | Cliente e novo advogado |
| Caso sem advogado elegível | Administradores ativos e verificados |
| Triagem, decisão, solicitação/conferência de complemento | Cliente |
| Resposta ao complemento, aceite/recusa da proposta, procuração devolvida | Advogado responsável |
| Proposta publicada, procuração disponibilizada/conferida ou devolvida para ajuste | Cliente |
| Geração de procuração, minuta interna e nota interna | Sem e-mail |
| Peça publicada, protocolo, movimentação e encerramento | Cliente |
| Criação, remarcação e conclusão de compromisso | Cliente |
| Documentos iniciados, recebidos, liberados ou recusados após submissão | Sem e-mail |
| Mensagem pública | Outra parte da conversa |
| Lembrete de audiência/compromisso | Cliente e advogado responsável |
| Lembrete de prazo interno e escalonamento de atraso | Advogado responsável |

Somente os tipos explícitos em `CASE_EMAIL_KINDS` geram e-mail. Eventos técnicos e tipos futuros não aprovados ficam no histórico/painel. O worker também cancela mensagens técnicas antigas ainda pendentes. Consultas, downloads e marcações de leitura não geram e-mail.

O envio respeita e-mail confirmado, conta ativa, preferência `case_email_enabled` e acesso atual ao caso; troca de responsável cancela mensagens pendentes do advogado anterior. Não há envio retroativo automático dos eventos antigos. O transporte tenta até cinco vezes, com intervalo crescente; após esgotar, exige recuperação operacional explícita. Aceitação SMTP não comprova chegada à caixa de entrada.

Executar `run_mail_queue` continuamente e acompanhar `check_mail --strict`. O worker local precisa de computador ligado, conexão e sessão ativa. Alterações na criação dos avisos exigem publicar a API; alterações no envio exigem reiniciar o worker.
