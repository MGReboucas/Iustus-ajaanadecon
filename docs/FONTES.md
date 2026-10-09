# Fontes e base de evidências

> Consulta em 16/09/2026. Documentação de serviços pode mudar; revisar compatibilidade na tarefa de integração.

## Evidência local

[package.json](../frontend/package.json), [package-lock.json](../frontend/package-lock.json), [app/page.js](../frontend/app/page.js), [app/layout.js](../frontend/app/layout.js), [tela de acesso](../frontend/app/acessar/page.tsx), [checkout](../frontend/app/checkout/page.js), [formulário PagBank](../frontend/app/checkout/PagBankTransparentForm.js), [sessão](../frontend/app/api/pagbank/session/route.js), [pagamento](../frontend/app/api/pagbank/payment/route.js), [configuração de acesso](ACESSO.md#configuração), [.gitignore](../.gitignore), estilos em `app/` e [HTML de referência](../frontend/index.html). As [diretrizes originais](DIRETRIZES_ORIGINAIS.md) registram o material fornecido pelo usuário.

O inventário e os achados financeiros decorrem da leitura estática desses arquivos, agora em frontend/. A organização posterior acrescentou a base em backend/, dependências travadas e verificações locais de build e testes; os resultados estão em Verificação. Não foram examinados registros produtivos nem executadas operações financeiras. Dependências instaladas e cache de build não foram tratados como código autoral do projeto.

## Referências primárias consultadas

| Fonte | Uso e limite |
| --- | --- |
| [Next.js — Authentication](https://nextjs.org/docs/app/guides/authentication) | Separação de autenticação, sessão e autorização; documentação atual não implica migração automática da versão instalada |
| [Next.js — use server](https://nextjs.org/docs/app/api-reference/directives/use-server) | Necessidade de verificar operações sensíveis no servidor |
| [Django — Autenticação](https://docs.djangoproject.com/en/5.2/topics/auth/) | Identidade e permissões do backend aprovado; versão de implantação ainda será fixada |
| [Django — Sessões](https://docs.djangoproject.com/en/5.2/topics/http/sessions/) | Sessões persistidas, cookies, rotação e revogação; vínculo ao portal é controle adicional da aplicação |
| [Django — CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/) | Proteção explícita no login, token AJAX e header X-CSRFToken |
| [Django — Transações](https://docs.djangoproject.com/en/5.2/topics/db/transactions/) | atomic e on_commit; a outbox durável é uma decisão de arquitetura da aplicação |
| [Django — Admin](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/) | Ferramenta interna; não substitui o fluxo de trabalho e os dashboards |
| [DRF — Autenticação](https://www.django-rest-framework.org/api-guide/authentication/) | SessionAuthentication retorna 403 para requisição anônima negada; login precisa de proteção CSRF explícita |
| [DRF — Permissões](https://www.django-rest-framework.org/api-guide/permissions/) | Verificação de objeto não substitui filtro de queryset e validação na criação |
| [PagBank — Notificações](https://developer.pagbank.com.br/v1.0/docs/api-notificacao-v1) | Referência para conferir integração existente baseada em transações; produto habilitado ainda pendente |
| [PagBank — Webhooks](https://developer.pagbank.com.br/reference/webhooks) | Estados e eventos financeiros; não presumir compatibilidade de payload entre APIs |
| [LGPD — texto compilado](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) | Base normativa para revisão jurídica do inventário e das políticas |
| [ANPD — Guia de segurança da informação](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/processo-guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte.pdf) | Referência de organização de controles; enquadramento da operação não foi presumido |
| [CONTRAN — Resolução 900/2022](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-contran/resolucao-contran-no-900-de-9-de-marco-de-2022) | Distinção entre defesa prévia e recursos de multas; verificar órgão e procedimento no caso concreto |
| [OAB — Código de Ética](https://www.oab.org.br/leisnormas/legislacao/resolucoes/02-2015) | Delimitação contratual da prestação e extensão da atuação |
| [OAB/RN — Tabela de honorários](https://www.oabrn.org.br/pagina/tabela-de-honorarios) | Página oficial com edição 2026 para revisão pelo escritório; valores por ato não foram definidos nesta entrega |

## O que constitui proposta própria

Next.js/TypeScript, Python/Django/DRF e PostgreSQL compõem a arquitetura aprovada pelo usuário. Organização modular, outbox, isolamento de sessões, limites de arquivo, metas de capacidade/desempenho, janelas operacionais e estimativas são decisões ou propostas de engenharia desta documentação. Não atribuí-las aos fornecedores como requisitos oficiais nem tratá-las como aprovação jurídica. Django 5.2.17 e DRF 3.18.1 estão travados na fundação local; isso não define homologação produtiva. Datas resultam apenas do backlog e do calendário declarados em [Cronograma](CRONOGRAMA.md).

## Referências do incremento de acesso

- [Next.js: atualização de segurança de agosto de 2026](https://nextjs.org/blog/august-2026-security-release): atualização do frontend para 15.5.25 dentro da linha 15.
- [React: avisos de segurança de Server Components](https://react.dev/blog/2025/12/11/denial-of-service-and-source-code-exposure-in-react-server-components): React/React DOM atualizados para 19.1.9.
- [PyOTP](https://pyauth.github.io/pyotp/): TOTP e prevenção de reuso.
- [Fernet](https://cryptography.io/en/latest/fernet/): criptografia autenticada dos segredos de MFA e da fila de identidade.

Versões exatas estão nos lockfiles; atualização não equivale a auditoria completa.
