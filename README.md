# IUSTUS — Defesa Jurídica Online

Plataforma por assinatura para solicitar, acompanhar e receber defesas jurídicas online. A jornada pretendida reúne contratação, envio de casos e documentos, procuração, acompanhamento pelo cliente e preparação da defesa por advogado designado.

**Operação local (29/09/2026):** [Perfil, usuários, privacidade, lembretes e manutenção](docs/OPERACAO_LOCAL.md) implementados sem serviços externos. S3 preparado e testado com simulador, desativado por padrão em produção.

**Procurações e dossiê (29/09/2026):** [Geração PDF e exportação privada](docs/PROCURACOES_EXPORTACAO.md) integradas ao dashboard e validadas localmente.

**Incremento de 29/09/2026:** [Fluxo de atendimento no dashboard](docs/FLUXO_ATENDIMENTO.md): liberação administrativa, procuração, peça revisada, protocolo, compromissos e encerramento implementados localmente.

**Estado anterior em 25/09/2026:** acesso com MFA, casos/triagem e documentos privados implementados. Novo incremento local de [dashboard e comunicação](docs/DASHBOARD_COMUNICACAO.md): indicadores reais por perfil, próximos passos, conversa por caso, notas internas e avisos com leitura persistida. Scanner real, armazenamento produtivo, assinatura, integração financeira e e-mails de novidades do caso permanecem pendentes.

[Documentação completa](docs/README.md) · [Estado atual](docs/ESTADO_ATUAL.md) · [MVP](docs/MVP.md) · [Backlog](docs/BACKLOG.md) · [Cronograma](docs/CRONOGRAMA.md)

## Objetivo e proposta comercial

**Operação confirmada:** escritório próprio no Rio Grande do Norte, com dois advogados inicialmente, para multas de trânsito e direito civil em geral, **excluindo apenas família e sucessões do escopo civil**. No civil, a atuação é completa: ajuizar, defender, protocolar e acompanhar; consumo, imobiliário e demais matérias civis permanecem incluídos. Checklists, abrangência territorial e fases incluídas no preço estão em detalhamento nas [Regras do serviço](docs/REGRAS_DO_SERVICO.md). Essa equipe jurídica é distinta do desenvolvedor único considerado no cronograma.

Permitir que o cliente com assinatura confirmada envie um caso, forneça documentos e procuração e acompanhe o trabalho do escritório, incluindo ajuizamento, defesa, protocolos e andamento civil, com acesso restrito e histórico rastreável.

A oferta existente é de **R$ 547 por ano**, com uso ilimitado durante a vigência e anúncio de pagamento à vista ou em **6 ou 12 vezes**. Categorias atendidas, condições do serviço, política de renovação e tratamento de casos após expiração ainda dependem de validação. O formulário atual oferece opções até 12 parcelas retornadas pelo provedor; a divergência com a comunicação será resolvida no backlog.

A landing apresenta proposta de valor, jornada em três etapas, benefícios, plano anual, FAQ, layout responsivo e identidade azul-marinho/dourado. O painel ilustrado é uma prévia; os depoimentos são modelos que precisam ser substituídos por relatos reais autorizados ou retirados antes da publicação.

## Estado do desenvolvimento

| Componente | Situação |
| --- | --- |
| Landing page e identidade visual | Código existente; revisão final de conteúdo/acessibilidade pendente |
| Checkout PagBank | SDK e rotas existentes; correções de segurança, conciliação e homologação pendentes |
| Login e cadastro | Cadastro, confirmação, login, recuperação e sessões persistentes testados localmente |
| Fundação técnica | Next.js/TypeScript, Django/DRF e PostgreSQL; MFA, isolamento de portais e worker de identidade |
| Casos e triagem | Rascunho, atribuição, triagem e complemento persistidos; submissão restrita a liberação de teste |
| Assinatura e documentos | Documentos implementados localmente; scanner/armazenamento produtivo e integração financeira pendentes |
| Dashboards e gestão jurídica | Indicadores, pendências, mensagens, notas internas e avisos; etapas processuais pendentes |
| Documentação do MVP | Revisão 1.5; acesso e triagem implementados e validação operacional pendente |
| Produção | Nenhuma evidência de homologação ou implantação verificada nesta etapa |

O levantamento identificou envio desnecessário de campos de cartão ao backend e exibição de aprovação sem confirmação de estado financeiro. Correções estão priorizadas em [Estado atual](docs/ESTADO_ATUAL.md) e [Segurança](docs/SEGURANCA.md). A existência do checkout não significa que esteja pronto para cobrança real.

## Arquitetura resumida

**Atual:** Next.js 15.5.25 / React 19.1.9 em `frontend/`, com acesso e painéis em TypeScript. Django 5.2.17 e DRF 3.18.1 em `backend/` implementam identidade persistida em PostgreSQL. Landing e código do checkout permanecem preservados; as rotas PagBank ainda estão no Next.js.

**Arquitetura aprovada:** Next.js + TypeScript no frontend; Python + Django + Django REST Framework no backend; PostgreSQL com Django ORM; armazenamento privado de objetos e worker Python separado com outbox transacional. Um repositório, com backend modular responsável por identidade, autorização, regras jurídicas e pagamentos. Fornecedores, versões, região e custos ainda serão validados. [Arquitetura e diagramas](docs/ARCHITECTURE.md) · [Modelo de dados](docs/DATABASE.md) · [API](docs/API.md).

**Portais aprovados:** cliente e equipe em origens separadas, sessões vinculadas ao portal e MFA obrigatório para profissionais. Localmente, cliente usa `localhost:3000` e equipe `127.0.0.1:3000`; o proxy Next.js encaminha `/api/v1` ao Django. Subdomínios reais, HTTPS e infraestrutura produtiva permanecem pendentes.

## Roadmap resumido

1. Validar documentação, escopo, calendário e dependências externas.
2. Preparar fundação técnica, identidade, pagamentos e vigência.
3. Implementar casos, documentos, dashboards e procurações.
4. Implementar histórico, comunicação, peças, registros externos e administração.
5. Consolidar segurança, privacidade, regressão e homologação.
6. Preparar produção, restauração, monitoramento e operação assistida.

Uma pessoa executará as tarefas sequencialmente, incluindo infraestrutura, testes e correções. A fase 2A explicita pagamentos e assinatura. O MVP prevê assinatura de procuração externa e protocolo registrado manualmente pelo advogado; integrações com tribunais e assinatura embutida ficam fora da primeira versão, conforme hipótese registrada em [Decisões](docs/DECISOES.md).

## Previsão do MVP

<!-- PLANEJAMENTO:INICIO -->

**Início de referência:** 16/09/2026

**Desenvolvedor:** 1 · **Carga:** 8h/dia · **Carga semanal:** 40h

**Horas técnicas planejadas:** 1360h

**Contingência:** 336h (24,71% efetivos)

**Total:** 1696h · **Dias de capacidade:** 212 · **Semanas de capacidade:** 42,4

**MVP Feature Complete:** 12/05/2027

**Homologação concluída:** 24/06/2027

**Produção validada:** 08/07/2027

Calendário provisório de segunda a sexta-feira; feriados, férias e ausências ainda não descontados. As datas dependem da confirmação do calendário e das dependências externas. Detalhamento, reservas e dependências: [Cronograma](docs/CRONOGRAMA.md).

<!-- PLANEJAMENTO:FIM -->

## Executar localmente

O [guia de casos e triagem](docs/CASOS.md) explica a liberação local, distribuição de casos e revisão pelo advogado. Consulte também [documentos privados](docs/DOCUMENTOS.md) e [dashboard e comunicação](docs/DASHBOARD_COMUNICACAO.md).

Siga o [guia de acesso local](docs/ACESSO.md) para preparar PostgreSQL, configurar os dois portais, iniciar o worker e criar o primeiro administrador. Os comandos abaixo iniciam somente o frontend.

Frontend verificado com Node.js 24.14.1; dependências travadas em `frontend/package-lock.json`. Na raiz:

```bash
npm run frontend:install
npm run dev
```

`frontend:install` executa `npm ci` dentro de `frontend/`; os scripts da raiz encaminham os comandos para essa pasta. Em PowerShell com restrição a scripts, use `npm.cmd` no lugar de `npm`. Abra [localhost:3000](http://localhost:3000). Executar apenas `npm ci` na raiz não instala o frontend.

Build e execução de produção local:

```bash
npm run build
npm start
```

Use `npm run typecheck` para verificar TypeScript. O backend tem instalação e comandos próprios em [backend/README.md](backend/README.md); o PostgreSQL local opcional está em [infra/README.md](infra/README.md). Instruções do frontend: [frontend/README.md](frontend/README.md). Passar no build não comprova autenticação, segurança financeira ou homologação.

## Configuração PagBank

A rota `/checkout` usa layout próprio e o SDK de Checkout Transparente presente no código. A biblioteca cria sessão, identifica bandeira, consulta parcelas e tokeniza o cartão. Parcelas, juros e total dependem da conta e do provedor; não devem ser fixados arbitrariamente no frontend. O backend ainda precisa validar a cotação e o estado financeiro.

Copie `frontend/.env.example` para `frontend/.env.local` e preencha as credenciais da conta de teste:

```dotenv
PAGBANK_EMAIL=seu-email-de-vendedor
PAGBANK_TOKEN=seu-token-de-integracao
NEXT_PUBLIC_PAGBANK_SANDBOX=true
```

`PAGBANK_EMAIL` e `PAGBANK_TOKEN` são privados e usados exclusivamente no servidor. Não versionar valores. `NEXT_PUBLIC_PAGBANK_SANDBOX` é público e afeta o build; definir `false` somente após correções, testes, homologação e configuração produtiva coerente. O produto/API habilitado precisa ser confirmado antes de consolidar a integração. [Contratos](docs/API.md) · [Operação](docs/OPERACAO.md).

## Estrutura do repositório

```text
frontend/
├── app/                              # Páginas, CSS e rotas PagBank preservados
├── src/lib/api/                      # Base para integração HTTP TypeScript
├── index.html                        # Referência estática preservada
├── .env.example                      # Configuração do frontend/checkout legado
├── tsconfig.json
└── package.json / package-lock.json   # Dependências do frontend
backend/
├── manage.py
├── config/                           # URLs, ASGI/WSGI e settings local/test
├── apps/                             # Identity, billing, cases, documents, legal...
├── integrations/                     # PagBank, objetos, e-mail e scanner
├── jobs/                             # Estrutura reservada ao worker
├── tests/                            # Testes da fundação
├── .env.example
└── pyproject.toml / requirements.lock
infra/
├── compose.local.yaml                # PostgreSQL local opcional
├── proxy/                            # Diretrizes da entrada HTTPS
└── deploy/                           # Diretrizes de implantação
tests/e2e/                            # Estrutura para jornadas futuras
docs/                                 # Documentação e gerador de planejamento
package.json / package-lock.json       # Atalhos da raiz, sem dependências de runtime
.git/                                 # Repositório e histórico originais preservados
README.md
```

## Documentação

| Tema | Documentos |
| --- | --- |
| Produto | [Visão geral](docs/VISAO_GERAL.md), [Estado atual](docs/ESTADO_ATUAL.md), [MVP](docs/MVP.md), [Resumo executivo](docs/RESUMO_EXECUTIVO.md) |
| Especificação | [Requisitos funcionais](docs/REQUISITOS_FUNCIONAIS.md), [Não funcionais](docs/REQUISITOS_NAO_FUNCIONAIS.md), [Regras de negócio](docs/REGRAS_DE_NEGOCIO.md), [User stories](docs/USER_STORIES.md), [Casos de uso](docs/CASOS_DE_USO.md) |
| Experiência e acesso | [Permissões](docs/PERMISSOES.md), [Fluxos](docs/FLUXOS.md), [Telas](docs/TELAS.md) |
| Engenharia | [Arquitetura](docs/ARCHITECTURE.md), [Banco](docs/DATABASE.md), [API](docs/API.md), [Segurança](docs/SEGURANCA.md), [LGPD](docs/LGPD.md) |
| Execução | [Cronograma](docs/CRONOGRAMA.md), [Backlog](docs/BACKLOG.md), [Plano de commits](docs/PLANO_DE_COMMITS.md), [Rastreabilidade](docs/RASTREABILIDADE.md) |
| Qualidade e operação | [Testes](docs/TESTES.md), [Operação](docs/OPERACAO.md), [Riscos](docs/RISCOS.md), [Verificação documental](docs/VERIFICACAO.md) |
| Governança | [Índice](docs/README.md), [Decisões](docs/DECISOES.md), [Fontes](docs/FONTES.md), [Diretrizes originais](docs/DIRETRIZES_ORIGINAIS.md) |

Para recalcular o planejamento e conferir a documentação:

```bash
node docs/planejamento/gerar.cjs
node docs/planejamento/gerar.cjs --check
node docs/planejamento/verificar.cjs
```

A fonte única de requisitos e estimativas está em [dados.cjs](docs/planejamento/dados.cjs). As diretrizes originais das seções 27–39 foram preservadas integralmente no documento vinculado acima; as seções 1–26 não foram fornecidas.

## Próximo passo e limite desta etapa

**Incremento atual:** [dashboard e comunicação](docs/DASHBOARD_COMUNICACAO.md), com contadores autorizados, pendências, mensagens, notas internas e avisos persistidos. **Próxima etapa de comunicação:** e-mails de novidades do caso com outbox e retry. Pagamentos e assinatura (DEV-012 a DEV-016 e DEV-062), scanner real, armazenamento produtivo e infraestrutura/políticas continuam necessários antes da operação comercial. A estimativa de 1696h continua sendo a baseline integral, sem desconto automático do trabalho realizado.

A comunicação jurídica, critérios de atendimento, modelos, condições comerciais, retenção de dados e fluxos de contratação devem ser revisados pelos responsáveis da operação antes da publicação.
