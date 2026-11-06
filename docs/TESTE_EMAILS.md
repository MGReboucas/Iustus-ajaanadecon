# Validação do fluxo de emails

## Preparação

Aplicar migrações, iniciar o worker e executar `check_mail --strict --connect` com as configurações do ambiente. Usar contas e pagamentos de teste; não realizar cobranças reais para homologar emails. O perfil local grava arquivos, e as suítes automatizadas usam transporte em memória.

## Jornada para testar

| Ação | Resultado esperado |
| --- | --- |
| Confirmar pagamento de teste | Um email de ativação; repetir conciliação não duplica o email |
| Reenviar acesso antes da ativação | Apenas o link mais recente funciona; mensagens antigas na fila são canceladas |
| Estornar antes do envio | Ativação pendente cancelada; aviso de reversão, sem liberar associação |
| Ativar cadastro e recuperar senha | Link de uso único; recuperação expira em uma hora |
| Convidar advogado e reenviar convite | Convite mais recente válido, sem conceder acesso a outro papel |
| Enviar ocorrência | Confirmação ao cliente; atribuição ao advogado ou aviso à administração |
| Fazer triagem e pedir complemento | Avisos ao cliente; resposta avisa o advogado |
| Publicar proposta e responder | Cliente recebe proposta; advogado recebe aceite/recusa |
| Disponibilizar/devolver/conferir procuração | Avisos ao destinatário da próxima ação |
| Publicar peça, registrar protocolo ou movimentação | Aviso ao cliente, sem conteúdo jurídico privado no email |
| Enviar mensagem pública | Aviso à outra parte; nota interna não envia ao cliente |
| Criar ou remarcar compromisso | Aviso da alteração; lembrete até 24h antes ou pendente |
| Deixar compromisso atrasado por 24h | Uma escalada ao advogado; sem repetição a cada ciclo |
| Concluir/remarcar compromisso antes do envio | Lembrete antigo cancelado |
| Encerrar atendimento | Aviso ao cliente e cancelamento de lembretes pendentes |
| Desativar emails de casos ou remover acesso | Emails de casos pendentes cancelados; emails transacionais continuam independentes da preferência |
| Recusar/cancelar/reverter pagamento | Aviso específico, deduplicado e revalidado antes do envio |
| Associação a sete dias do vencimento ou vencida há até sete dias | Um aviso por validade e etapa; renovação cancela aviso antigo |
| Abrir/responder solicitação de privacidade | Confirmação/aviso sem divulgar o texto do pedido ou da resposta |
| Simular indisponibilidade SMTP | Retentativas; após cinco falhas, alerta no log e health check não saudável |
| Recuperar mensagem com `retry_mail` | Nova tentativa com todas as validações, sem reenviar mensagens já enviadas/canceladas |

## Evidências e limites

`sent_at` comprova aceitação pelo transporte SMTP. Confirme também chegada, pasta de spam, logo, botão, acentos e cabeçalhos SPF/DKIM/DMARC na caixa de teste. SMTP não oferece confirmação de leitura nem eventos de bounce/complaint neste projeto.

O worker local depende do computador ligado, acordado, conectado e da sessão do usuário. A tarefa do Windows recupera processos encerrados e inicia no login. Disponibilidade independente do computador exige um worker hospedado e monitoramento externo.

Suíte completa com concorrência: `python manage.py test tests --settings=config.settings.test_postgres --noinput`, usando `TEST_DATABASE_URL` exclusivamente de um banco isolado. Nunca executar testes de banco contra produção.
