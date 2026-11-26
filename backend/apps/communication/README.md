# communication

Mensagens por caso, notas internas e notificações persistidas, com APIs e testes de autorização e concorrência.

O resumo do dashboard aplica o mesmo escopo de casos do domínio. Notificações e a fila CaseEmail são gravadas na mesma transação da movimentação, com deduplicação por evento e destinatário. Notas internas não geram aviso ao cliente. [Contrato e limites](../../../docs/DASHBOARD_COMUNICACAO.md).

## Destinatários dos e-mails

| Movimentação | Destinatário |
| --- | --- |
| Criação/edição de rascunho e documentos antes da submissão | Cliente |
| Submissão | Cliente, com relato, categoria, data e referência |
| Atribuição ou troca de advogado | Cliente e novo advogado |
| Caso sem advogado elegível | Administradores ativos e verificados |
| Triagem, decisão, solicitação/conferência de complemento | Cliente |
| Resposta ao complemento, aceite/recusa da proposta, procuração devolvida | Advogado responsável |
| Proposta publicada, procuração gerada/disponibilizada/conferida ou devolvida para ajuste | Cliente |
| Minuta interna e nota interna | Apenas advogado responsável |
| Peça publicada, protocolo, movimentação e encerramento | Cliente |
| Criação, remarcação e conclusão de compromisso | Cliente |
| Documentos iniciados, recebidos, liberados ou recusados após submissão | Cliente e advogado responsável |
| Mensagem pública | Outra parte da conversa |
| Lembrete de audiência/compromisso | Cliente e advogado responsável |
| Lembrete de prazo interno e escalonamento de atraso | Advogado responsável |

Eventos futuros registrados por `changed`/`record` recebem aviso genérico, respeitando a visibilidade pública/interna. Consultas, downloads e marcações de leitura não são movimentações e não geram e-mail. Falhas transitórias de infraestrutura não são movimentações jurídicas.

O envio respeita e-mail confirmado, conta ativa, preferência `case_email_enabled` e acesso atual ao caso; troca de responsável cancela mensagens pendentes do advogado anterior. Não há envio retroativo automático dos eventos antigos. O transporte tenta até cinco vezes, com intervalo crescente; após esgotar, exige recuperação operacional explícita. Aceitação SMTP não comprova chegada à caixa de entrada.

Executar `run_mail_queue` continuamente e acompanhar `check_mail --strict`. O worker local precisa de computador ligado, conexão e sessão ativa. Alterações na criação dos avisos exigem publicar a API; alterações no envio exigem reiniciar o worker.
