# Decisões, hipóteses e dependências

> Base em 16/09/2026 · Situações discriminadas abaixo: confirmações do usuário, propostas de engenharia e decisões ainda pendentes.

## Definições confirmadas pelo usuário

| Definição | Confirmação | Limite da confirmação |
| --- | --- | --- |
| Áreas de atuação | Multas de trânsito e direito civil em geral, excluindo apenas família e sucessões do civil | Checklists, etapas, abrangência territorial e cobertura financeira da assinatura ainda serão detalhados |
| Modelo operacional | Escritório próprio sediado no Rio Grande do Norte | Identificação do prestador, cidade e abrangência territorial ainda não informadas |
| Atuação civil | Atuação completa: ajuizar, defender, protocolar e acompanhar; demais matérias civis incluídas, inclusive consumo e imobiliário | Fases cobertas pelo contrato e pelo preço da assinatura ainda serão delimitadas; lista de exemplos não restringe as matérias aceitas |
| Equipe jurídica inicial | Dois advogados | Jornada, especialidades, capacidade por caso e responsáveis nominais ainda não informados |
| Portais | Área do cliente separada do portal profissional por subdomínio | Domínio real, configuração de sessões e implantação ainda pendentes |
| Stack de destino | Next.js + TypeScript no frontend; Python + Django + Django REST Framework no backend; PostgreSQL | Decisão aprovada; versões locais travadas; identidade implementada; hospedagem pendente |

As duas vagas jurídicas não alteram a premissa técnica de um desenvolvedor, 8h/dia. A proposta detalhada de atendimento e as perguntas restantes estão em [Regras do serviço](REGRAS_DO_SERVICO.md). Confirmação de área não equivale à inclusão irrestrita de todas as demandas ou fases no preço anunciado.

## Decisões de arquitetura

| ID | Proposta e justificativa | Alternativa / consequência | Situação |
| --- | --- | --- | --- |
| ADR-001 | Proposta original: backend e frontend no Next.js | Preservada como histórico; substituída por ADR-010 após decisão do usuário | Superada |
| ADR-002 | PostgreSQL com Django ORM e migrações Django versionadas | Frontend não acessa banco; provedor gerenciado e versão do banco serão homologados em DEV-005/006 | Tecnologia aprovada; infraestrutura pendente |
| ADR-003 | Identidade Django e sessões persistidas, vinculadas a portal; MFA da equipe por componente mantido | Django concentra credenciais; MFA TOTP, convites e isolamento de portais implementados e testados localmente; regras por caso pendentes | Base definida por ADR-010; PyOTP/Fernet implementados; operação produtiva a homologar |
| ADR-004 | Armazenamento de objetos privado e URLs curtas, com quarentena e scanner | Não persistir anexos no filesystem efêmero do deploy; provedor e região dependem de EXT-03 | Proposta |
| ADR-005 | Outbox em PostgreSQL e worker Python do mesmo backend, com retry, lease e fila de falhas | Executor persistente separado da API; não pressupor Redis/Celery nem usar só callback em memória | Desenho técnico da arquitetura aprovada |
| ADR-006 | Preservar PagBank como provedor e validar produto/API habilitados antes de implementar contrato final | Código atual usa sessão/checkout transparente e XML; não misturar enums e autenticação de APIs diferentes | Bloqueada por EXT-01 |
| ADR-007 | Frontend em TypeScript de forma incremental; backend Python com serializers DRF e serviços de domínio | Preservar landing; cliente HTTP não duplica autorização nem regras de pagamento | Atualizada por ADR-010 |
| ADR-008 | Assinatura de procuração externa e protocolo manual no MVP | Integrações automáticas requerem escopo, fornecedor, validação jurídica e nova estimativa | Hipótese H-04 |
| ADR-009 | Portais cliente e profissional em subdomínios distintos; /api/v1 sob a mesma origem de cada portal encaminha ao Django | Cookies por host e sessão vinculada ao portal; backend compartilhado valida acesso; infraestrutura não é isolada só pelo subdomínio | Direção aprovada; detalhada em Arquitetura/API e estimada em DEV-060/061/063 |
| ADR-010 | Backend Python com Django e Django REST Framework; frontend Next.js + TypeScript; PostgreSQL e worker separado | Um repositório e um backend modular, sem microserviços; acrescenta operação de Python e contrato HTTP, aproveitando domínio do desenvolvedor nas duas linguagens | Aprovada explicitamente pelo usuário nesta revisão |

Registrar decisão final, data, responsável, alternativa descartada e impacto na baseline ao validar cada ADR. Seleção concreta de fornecedores deve revisar documentação oficial compatível com a versão adotada, custos, exportação de dados e localização do tratamento.

**Impacto da escolha de arquitetura:** DEV-059 a DEV-064 acrescentaram uma estimativa de 80h técnicas para fundação Django, entrada por subdomínio, sessões separadas, retirada das rotas financeiras antigas, testes entre serviços e implantação coordenada. Esse valor é hipótese de planejamento, não custo obrigatório do framework. As tarefas de domínio passam a usar Django; a contingência e as datas são recalculadas pela fonte única. Após autorização para organizar o projeto, foi criado o monorepositório e implementado o primeiro incremento de acesso com PostgreSQL, MFA e testes de navegador. Isso não conclui as tarefas nem representa homologação produtiva; a baseline ainda não é um saldo de horas restantes.

## Hipóteses de negócio

| ID | Hipótese usada no planejamento | Quem valida | Antes de |
| --- | --- | --- | --- |
| H-01 | Atualização de 07/10/2026: anual com renovação automática no mesmo parcelamento e cancelamento da próxima renovação confirmado; detalhes operacionais pendentes | Produto confirmou; operação detalha | DEV-016 |
| H-02 | Preservação dos casos existentes confirmada em 07/10/2026. Associação ativa para novas submissões; detalhar estorno e contestação | Produto confirmou preservação; responsável jurídico detalha | DEV-016 |
| H-03 | Advogado responsável pode revisar e publicar sua própria peça; etapa de revisão é obrigatória e explícita | Responsável jurídico | DEV-034 |
| H-04 | Atuação civil completa pelo escritório confirmada; assinatura externa e registro manual dos atos praticados nos sistemas oficiais permanecem como desenho técnico proposto, sem integração automática | Produto + responsável jurídico | Fechamento de escopo DEV-002 |
| H-05 | Oferta permite 1, 6 ou 12 parcelas quando disponibilizadas pelo provedor; outras parcelas não entram sem mudança de comunicação | Produto + financeiro | DEV-013 |
| H-06 | Escritório próprio no RN, dois advogados, multas e civil em geral sem família/sucessões confirmados; pessoa física adulta e critérios individuais de elegibilidade permanecem como hipóteses | Produto + responsável jurídico | DEV-017 |

Prazos por categoria, checklists, atendimento urgente, representação de terceiros/menores e motivos individuais de recusa precisam ser definidos em DEV-002. A abrangência civil já está confirmada em RN-025; não reabrir essa escolha como pendência nem limitar o catálogo aos exemplos. A definição das áreas não resolve por si só a cobertura financeira de todas as etapas.

## Dependências externas

| ID | Insumo | Responsável externo | Marco necessário | Efeito da ausência |
| --- | --- | --- | --- | --- |
| EXT-01 | Conta PagBank habilitada, credenciais de sandbox, produto/API e processo de homologação confirmados | Titular da conta / suporte PagBank | DEV-012; M3 | Bloqueia pagamento real e sua previsão |
| EXT-02 | Escopo jurídico, modelos, política de assinatura, retenção, textos e aceite profissional | Responsável jurídico / responsável pelo tratamento | DEV-002, DEV-028, DEV-042; M9 | Bloqueia decisões de domínio e publicação |
| EXT-03 | Provedores e orçamento para hospedagem, banco, objetos, scanner, e-mail, monitoramento e backup; domínio e DNS | Proprietário / responsável financeiro | DEV-006; M10 | Bloqueia ambientes e produção |
| EXT-04 | Calendário efetivo do desenvolvedor, início real, feriados locais, férias e ausências | Desenvolvedor / proprietário | Baseline do cronograma | Datas publicadas permanecem condicionais |
| EXT-05 | Cliente e advogado disponíveis para homologação e responsável pelo aceite | Operação | DEV-049 a DEV-051 | Espera desloca M9 e M10 |
| EXT-06 | Responsável e cobertura operacional após lançamento, canal de incidente e contatos dos fornecedores | Operação | DEV-052; M10 | Não autoriza lançamento sem atendimento operacional |

Horas de reunião, preparação e acompanhamento do desenvolvedor estão nas tarefas. Horas de advogado, titular da conta e outros terceiros não integram a carga técnica. Duração das esperas não foi inventada; replanejar quando forem conhecidas.

## Custos a orçar

Itens mensais: hospedagem web, worker, banco, objetos e tráfego, verificação de arquivos, e-mail, logs e monitoramento. Itens variáveis: taxas de pagamento, armazenamento crescente, exportações e mensagens. Itens externos: revisão jurídica e assinatura eletrônica escolhida pela operação. Sem região, volume e fornecedores confirmados, não há orçamento monetário confiável nesta versão; obter cotações em EXT-03 antes de contratar.
