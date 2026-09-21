# Resumo executivo do planejamento

> Revisão 1.5 · Base: 16/09/2026 · Arquitetura aprovada; validação operacional pendente.

**Situação:** acesso, casos/triagem e documentos privados implementados localmente. Scanner real e armazenamento produtivo aguardam homologação. Baseline e hipóteses operacionais aguardam validação. As horas abaixo representam a estimativa integral, não o saldo restante.

Stack atual: Next.js 15.5.25, React 19.1.9 e TypeScript incremental; Django 5.2.17 e DRF 3.18.1 com PostgreSQL, cadastro, sessões por portal, MFA e worker de e-mails de identidade. PagBank permanece no legado Next.js; casos possuem rascunho, atribuição e triagem. Arquivos e elegibilidade financeira continuam pendentes.

Arquitetura aprovada: Next.js + TypeScript no frontend, Python + Django REST Framework no backend, PostgreSQL e worker Python separado. DEV-059 a DEV-064 acrescentam 80h técnicas para integração, isolamento dos portais e operação; reserva recalculada por fase. A integração dos portais foi testada localmente. Contrato OpenAPI, subdomínios reais e operação produtiva ainda não foram concluídos.

- Requisitos funcionais: 43.
- Requisitos não funcionais: 18.
- Regras de negócio: 25.
- User stories: 43.
- Tarefas do backlog: 64.

**Início de referência:** 16/09/2026

**Desenvolvedor:** 1 · **Carga:** 8h/dia · **Carga semanal:** 40h

**Horas técnicas planejadas:** 1360h

**Contingência:** 336h (24,71% efetivos)

**Total:** 1696h · **Dias de capacidade:** 212 · **Semanas de capacidade:** 42,4

**MVP Feature Complete:** 12/05/2027

**Homologação concluída:** 24/06/2027

**Produção validada:** 08/07/2027

Calendário provisório de segunda a sexta-feira; feriados, férias e ausências ainda não descontados. As datas dependem da confirmação do calendário e das dependências externas.

**Próxima tarefa recomendada:** pagamentos e assinatura, iniciando por DEV-012/013. O incremento de [documentos privados](DOCUMENTOS.md) está implementado localmente; scanner real e armazenamento produtivo aguardam homologação. Antes de cobrança/publicação, corrigir o checkout e homologar dependências produtivas. Os testes locais não significam aceite integral dos requisitos nem aprovação operacional.
