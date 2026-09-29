# Backend Django

Django 5.2.17 + DRF 3.18.1, organizado por domínio. Identidade implementa cadastro, confirmação, login, recuperação, convite de advogado, MFA TOTP, sessões por portal, auditoria e fila durável de e-mails. GET /api/v1/health/ verifica somente o processo. Casos têm rascunho, atribuição, triagem, complemento e histórico; documentos privados têm upload, versões, quarentena, worker e download autorizado. Pagamentos continuam pendentes. [Casos](../docs/CASOS.md) · [Documentos](../docs/DOCUMENTOS.md). Django Admin não está publicado.

Instalação, PostgreSQL isolado, configuração, primeiro administrador e testes: [Acesso local](../docs/ACESSO.md). A venv e os segredos são locais e ignorados pelo Git. Dependências estão em requirements.lock; não substituir as chaves persistentes ao reiniciar.

Em backend/, executar pelo Python da venv:

~~~powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test tests --settings=config.settings.test_postgres --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test
~~~

Settings local usa HTTP/loopback, DEBUG e e-mails em arquivos. Testes usam bancos separados; SQLite em memória não verifica concorrência PostgreSQL. Settings produtivos, SMTP e subdomínios reais ainda não foram homologados. [Infraestrutura](../infra/README.md) · [Segurança](../docs/SEGURANCA.md) · [Operação](../docs/OPERACAO.md).

Para executar a suíte com inspeção de PDF, instalar `pip install -r requirements-test.txt` dentro de backend. Produção utiliza somente requirements.lock (ou requirements-production.txt).
