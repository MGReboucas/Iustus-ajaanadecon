# Verificação da documentação e do incremento

## Incremento de documentos — 21/09/2026

47 testes Django passaram no PostgreSQL, incluindo concorrência de versões e isolamento dos documentos. Build e TypeScript passaram. Quatro jornadas Playwright passaram no Edge instalado, incluindo upload, bloqueio em quarentena, download pelo cliente/advogado e complemento com anexo em tela de 390 px, sem transbordamento horizontal. Testes de scanner usam respostas controladas, inclusive um servidor TCP para o protocolo ClamAV; scanner real e armazenamento produtivo ainda não foram homologados. [Escopo, comandos e limitações](DOCUMENTOS.md). As evidências de 16/09 abaixo são históricas.

> Evidências de 16/09/2026. Testes locais não equivalem a homologação produtiva.

## Planejamento

A fonte canônica conserva 43 requisitos funcionais, 18 não funcionais, 25 regras, 43 histórias e 64 tarefas. Baseline integral: 1360h técnicas + 336h de reserva = 1696h, 212 dias úteis de referência; início 16/09/2026 e término 08/07/2027, sem descontar feriados e ausências. Este incremento não recalcula automaticamente esforço restante nem declara aceite integral. [Cronograma](CRONOGRAMA.md) · [Resumo](RESUMO_EXECUTIVO.md).

Gerador e verificador conferem catálogos, cobertura, dependências, links locais, blocos Markdown/Mermaid, índice e cálculo independente do prazo. Executar na raiz:

~~~bash
node docs/planejamento/gerar.cjs --check
node docs/planejamento/verificar.cjs
git diff --check
~~~

O texto de [Diretrizes originais](DIRETRIZES_ORIGINAIS.md) permanece preservado, inclusive quebras Markdown intencionais. As contagens de arquivos/links atuais são emitidas pelo verificador.

## Evidências técnicas

- A organização anterior preservou 14 arquivos por SHA-256 e o histórico; foi publicada no commit 4b8d21f. Neste incremento, acesso e dependências foram alterados intencionalmente; landing e código financeiro permanecem preservados.
- Build Next.js 15.5.25 / React 19.1.9 e verificação TypeScript local. Há aviso de CSS sobre valor start, sem falha de compilação.
- Django check e verificação de migrações sem divergência; 35 testes no PostgreSQL isolado, incluindo consumo concorrente do mesmo TOTP e disputa por versão de caso. SQLite é alternativa parcial e pula esses dois testes de locks.
- Quatro jornadas de navegador verificam cliente, equipe, isolamento e triagem com dados sintéticos. Comandos e bancos separados: [Acesso local](ACESSO.md).
- Ambiente verificado: Node 24.14.1, Python 3.14.3, Django 5.2.17, DRF 3.18.1 e PostgreSQL 18.6. CI configurado com PostgreSQL 17 e Chromium. [Workflow do acesso e38ea41](https://github.com/MGReboucas/Iustus-nextjs/actions/runs/35103577150) aprovado; isso não comprova execução remota das alterações posteriores de casos.

## Limites

PagBank, SMTP externo, scanner, restauração, carga, auditoria de segurança completa, subdomínios reais e deploy não foram homologados. Nenhuma cobrança ou mensagem externa foi enviada. Os achados financeiros AT-01 a AT-04 continuam em aberto. Aprovação de políticas, fornecedores, custos e calendário efetivo permanece pendente. Diagramas Mermaid tiveram validação textual; links externos não são testados pelo verificador local.
