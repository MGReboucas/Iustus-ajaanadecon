# Documentação da Iustus

> Revisão 1.5 · Levantamento: 16/09/2026 · Responsável técnico: desenvolvedor único. Acesso e incremento de casos/triagem integrados e testados localmente; validação das regras operacionais e contratuais ainda pendente.

Esta documentação descreve o código encontrado e propõe o MVP da plataforma de defesa jurídica por assinatura. Os documentos de planejamento não certificam operação em produção. A implantação, o aceite humano e as verificações de segurança ainda precisam ocorrer.

## Comece por aqui

1. [Resumo executivo](RESUMO_EXECUTIVO.md): escopo, quantidade de requisitos e previsão calculada.
2. [Estado atual](ESTADO_ATUAL.md): evidências, limitações e riscos encontrados no código.
3. [MVP](MVP.md) e [Decisões](DECISOES.md): limites da primeira entrega, hipóteses e responsáveis por validação.
4. [Arquitetura](ARCHITECTURE.md), [Banco](DATABASE.md) e [API](API.md): proposta de construção.
5. [Backlog](BACKLOG.md), [Cronograma](CRONOGRAMA.md) e [Testes](TESTES.md): sequência de trabalho e critérios de aceite.

## Catálogo completo

| Documento | Finalidade |
| --- | --- |
| [Visão geral](VISAO_GERAL.md) | Objetivo, usuários, jornada e indicadores |
| [Casos e triagem](CASOS.md) | Rascunho, distribuição, complemento, decisão e liberação local de testes |
| [Documentos privados](DOCUMENTOS.md) | Upload, versões, quarentena, scanner e download autorizado |
| [Dashboard e comunicação](DASHBOARD_COMUNICACAO.md) | Indicadores, próximos passos, mensagens, notas internas e avisos |
| [Fluxo de atendimento](FLUXO_ATENDIMENTO.md) | Liberação administrativa, trabalho jurídico, compromissos e encerramento |
| [Procurações e exportação](PROCURACOES_EXPORTACAO.md) | Modelos versionados, emissão PDF e dossiê privado |
| [Operação local](OPERACAO_LOCAL.md) | Perfil, usuários, privacidade, lembretes e manutenção sem serviços externos |
| [Acesso local](ACESSO.md) | Instalação, cliente, equipe, MFA, worker e testes do incremento implementado |
| [Estado atual](ESTADO_ATUAL.md) | Inventário verificável e lacunas |
| [MVP](MVP.md) | Escopo incluído, excluído e critérios de lançamento |
| [Requisitos funcionais](REQUISITOS_FUNCIONAIS.md) | Capacidades e critérios de aceite |
| [Requisitos não funcionais](REQUISITOS_NAO_FUNCIONAIS.md) | Metas técnicas verificáveis |
| [Regras de negócio](REGRAS_DE_NEGOCIO.md) | Invariantes e políticas propostas |
| [Regras do serviço](REGRAS_DO_SERVICO.md) | Áreas confirmadas, escritório próprio, dois advogados e cobertura em definição |
| [User stories](USER_STORIES.md) | Necessidades por ator |
| [Casos de uso](CASOS_DE_USO.md) | Jornadas, pré-condições e exceções |
| [Permissões](PERMISSOES.md) | Matriz de acesso e testes negativos |
| [Fluxos](FLUXOS.md) | Estados e diagramas de operação |
| [Telas](TELAS.md) | Inventário de interfaces e estados de UX |
| [Arquitetura](ARCHITECTURE.md) | Componentes atuais e propostos |
| [Banco](DATABASE.md) | Modelo de dados e invariantes |
| [API](API.md) | Contratos atuais e propostos |
| [Segurança](SEGURANCA.md) | Ameaças, controles e prioridades |
| [LGPD](LGPD.md) | Inventário e plano de governança de dados |
| [Cronograma](CRONOGRAMA.md) | Horas, reservas, marcos, datas e Gantt |
| [Backlog](BACKLOG.md) | Tarefas sequenciais executáveis |
| [Plano de commits](PLANO_DE_COMMITS.md) | Entregas pequenas e verificáveis |
| [Rastreabilidade](RASTREABILIDADE.md) | Ligações entre requisitos, histórias e tarefas |
| [Decisões](DECISOES.md) | Propostas técnicas, hipóteses e dependências externas |
| [Riscos](RISCOS.md) | Probabilidade, impacto, mitigação e gatilhos |
| [Testes](TESTES.md) | Estratégia e roteiro de aceite |
| [Operação](OPERACAO.md) | Implantação, restauração, alertas e incidentes |
| [Fontes](FONTES.md) | Evidências locais e referências primárias consultadas |
| [Resumo executivo](RESUMO_EXECUTIVO.md) | Indicadores do planejamento |
| [Diretrizes originais](DIRETRIZES_ORIGINAIS.md) | Texto original das seções 27–39 preservado |
| [Verificação documental](VERIFICACAO.md) | Checagens efetuadas e limites da revisão |

## Manutenção e controle de mudanças

Catálogos e estimativas ficam em [dados.cjs](planejamento/dados.cjs). O [gerador](planejamento/gerar.cjs) mantém requisitos, histórias, backlog, matriz, cronograma e resumo sincronizados. Não editar manualmente as tabelas geradas; alterar a fonte e executar os comandos abaixo na raiz:

```bash
node docs/planejamento/gerar.cjs
node docs/planejamento/gerar.cjs --check
node docs/planejamento/verificar.cjs
```

Documentos narrativos são editados diretamente. Toda mudança de escopo deve indicar motivo, requisitos afetados, horas, riscos e impacto nas datas; o responsável pelo produto aceita a nova baseline. Não registrar aprovação presumida. O desenvolvedor mantém evidências e status por tarefa, e revisa a previsão ao concluir cada fase.

**Vocabulário:** implementado = há código; validado = cenário executado com evidência; aprovado = responsável identificado aceitou; proposto = decisão técnica sugerida; hipótese = regra ainda não confirmada. Feature Complete encerra implementação do escopo, mas precede a regressão final, homologação e produção.
