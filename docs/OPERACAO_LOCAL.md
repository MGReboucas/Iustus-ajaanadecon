# Operação local do dashboard

Implementado e testado sem contas externas. Esta entrega não homologa S3, ClamAV, SMTP ou PagBank em produção.

## Perfil e acesso

Minha conta permite editar o nome de exibição e optar por e-mails do atendimento. A preferência não altera avisos no painel nem e-mails de autenticação. E-mail e perfil de autorização não são alteráveis por esse formulário.

Administradores consultam usuários com paginação e suspendem/reativam clientes e advogados com justificativa auditada. Toda alteração invalida sessões anteriores. Advogados com casos ativos precisam ter esses casos redistribuídos antes da suspensão. Administradores não podem ser suspensos por essa interface. Alterações concorrentes exigem atualização da lista.

## Privacidade

Clientes e profissionais abrem solicitações de acesso, correção, exclusão ou outros temas e veem apenas as próprias solicitações. Administradores veem a fila e registram uma resposta definitiva. Solicitações e respostas são auditadas; textos não entram no log de auditoria. A interface registra a análise e a resposta: não executa exclusão, anonimização ou entrega integral de dados automaticamente. A política de retenção e o procedimento de atendimento precisam ser definidos pelo escritório.

## E-mails e lembretes

Eventos e mensagens públicas geram uma fila transacional. Notas internas não geram e-mails ao cliente. O corpo enviado é genérico e contém somente um link para entrar no portal: não inclui relato, título, mensagem ou anexos. Antes da tentativa, o worker revalida conta ativa, verificação, preferência e vínculo atual com o caso.

Lembretes são criados para compromissos pendentes nas próximas 24 horas ou já vencidos: prazos internos somente para o advogado; audiências e etapas para advogado e cliente. Há um aviso por compromisso, data e destinatário. Conclusão, encerramento e remarcação invalidam e-mails antigos ainda na fila. Avisos já entregues não podem ser recolhidos. A entrega é ao menos uma vez: uma queda depois da aceitação pelo servidor pode resultar em duplicidade. São até cinco tentativas com espera progressiva e lease; erros guardam só o nome da classe, sem conteúdo sensível.

No diretório backend, usando o ambiente virtual:

```powershell
python manage.py migrate
python manage.py run_operations --once
python manage.py run_operations
```

`--once` agenda lembretes, processa até 100 pares de mensagens de acesso/atendimento e remove exportações expiradas. O modo contínuo repete a cada 30 segundos. O settings local grava e-mails em `.local/mail`, sem enviar pela rede. Esse diretório contém links de acesso sensíveis e não deve ser versionado. A limpeza mantém os metadados das exportações. Documentos jurídicos originais não são apagados.

`deliver_case_mail --once` drena apenas e-mails de atendimento disponíveis; `scan_documents` continua sendo um worker separado e exige ClamAV. Arquivos enviados ficam em quarentena até a verificação real. O worker de operações não simula resultado de antivírus.

O manifesto Render passa a usar `run_operations` no worker existente. Não foi aplicado nem publicado.

## Armazenamento opcional

O adaptador S3 mantém objetos privados e imutáveis, valida tamanho e checksum e transmite downloads pela API autorizada. A gravação usa `IfNoneMatch`, checksum SHA-256 e criptografia SSE-S3 conforme a [referência oficial PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html). Os testes usam Moto, sem acessar um bucket real. Homologar compatibilidade do provedor, IAM, bloqueio de acesso público, retenção, backup e restauração antes de habilitar.

Produção permanece com `DOCUMENT_STORAGE_BACKEND=disabled` por padrão. A futura ativação requer `s3`, `DOCUMENT_S3_BUCKET`, região e identidade IAM ou par `DOCUMENT_S3_ACCESS_KEY`/`DOCUMENT_S3_SECRET_KEY`; endpoint HTTPS opcional, prefixo e estilo opcionais. Exige também host privado e porta do scanner. O protocolo ClamAV deve permanecer em rede privada, conforme a [documentação do ClamAV](https://docs.clamav.net/manual/Usage/Scanning.html).

## Validação

Testes PostgreSQL cobrem isolamento, CSRF, revogação de sessão, proteção de administradores, conflito de versão, privacidade, deduplicação, opt-out, transferência de caso, remarcação, retry e armazenamento S3 simulado. A jornada Playwright cobre perfil persistido, solicitação e resposta de privacidade, suspensão e saída do cliente, além do fluxo jurídico completo.

Continuam externos: provisionamento/homologação de S3, scanner, SMTP, PagBank, deploy, política de retenção e operação real. Recuperação excepcional de MFA sem fatores e gestão de administradores continuam procedimentos operacionais, sem atalho inseguro na interface.
