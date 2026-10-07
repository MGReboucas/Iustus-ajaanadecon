// Fonte única dos catálogos e estimativas. Gerar documentos: node docs/planejamento/gerar.cjs
const parse = (text) => text.trim().split('\n').map(line => line.split('|').map(value => value.trim()));
const prefix = (name, n) => `${name}-${String(n).padStart(3, '0')}`;
const rf = parse(`
Apresentação pública|Visitante|Conhecer plano, limites do serviço e canais de acesso|Preço, condições e links de termos coincidem com a política aprovada; nenhum depoimento fictício aparece como real
Cadastro de cliente|Cliente|Criar conta com e-mail verificado e aceite versionado|E-mail duplicado não cria outra conta; token expirado não verifica cadastro
Login e logout|Usuário|Autenticar e encerrar a própria sessão|Credenciais válidas abrem sessão; logout impede reutilização; falhas não revelam existência da conta
Recuperação de acesso|Usuário|Recuperar senha por token temporário de uso único|Token usado ou expirado é rejeitado; alteração revoga sessões anteriores
Controle de sessões|Administrador|Bloquear conta e revogar sessões|Conta bloqueada perde acesso em nova requisição protegida, inclusive com cookie anterior
Convite de advogado|Administrador|Convidar advogado com perfil aprovado pela operação|Convite expira; cliente não consegue atribuir a si próprio papel de advogado
Perfil do cliente|Cliente|Consultar e corrigir os próprios dados cadastrais|Atualização valida campos, exige revalidação de e-mail e não permite alterar papel ou assinatura
Checkout seguro|Cliente|Contratar o plano com preço e parcelas confirmados pelo servidor|Payload interno não contém PAN, CVV ou validade; parcela adulterada é rejeitada; pedido pertence ao cliente autenticado
Conciliação de pagamento|Sistema|Confirmar estados de pagamento por comunicação verificada com o provedor|Evento repetido não duplica ativação; código de transação sem confirmação não libera acesso
Vigência da assinatura|Cliente|Consultar situação, início e fim do período contratado|Vigência é persistida; expiração bloqueia novas submissões; histórico continua acessível conforme política aprovada
Abertura de caso|Cliente|Salvar rascunho e submeter relato, categoria e documentos|Rascunho pode ser incompleto; submissão valida campos e vigência no servidor; reenvio não duplica caso
Triagem de caso|Advogado|Avaliar elegibilidade e suficiência das informações|Somente profissional designado registra aceite, recusa justificada ou pendência; família e sucessões ficam fora do escopo civil conforme RN-025, demais matérias civis não são recusadas só por não constarem dos exemplos; cliente visualiza motivo publicável
Atribuição de caso|Administrador|Designar e substituir o advogado responsável|Há um responsável ativo; troca registra motivo e revoga acesso do anterior
Estados do caso|Advogado|Atualizar o andamento pelas transições permitidas|Transição inválida ou concorrente retorna conflito sem alterar histórico
Solicitação de complemento|Advogado|Solicitar documentos ou esclarecimentos ao cliente|Solicitação tem descrição, autor e estado; resposta mantém vínculo ao caso e permite resolução explícita
Upload privado|Cliente|Anexar arquivos permitidos ao próprio caso|Arquivo acima de 20 MiB ou tipo incompatível é recusado; arquivo fica em quarentena até verificação
Versões de documentos|Usuário autorizado|Substituir documento sem apagar versões anteriores|Nova versão preserva hash, autor e referência anterior; download de versão antiga segue a mesma autorização
Visualização e download|Usuário autorizado|Acessar documentos do caso sob autorização|URL temporária só é emitida para usuário autorizado e arquivo liberado; outro cliente recebe 404
Dashboard do cliente|Cliente|Ver casos, pendências, assinatura e últimas atualizações|Listagem paginada contém apenas dados próprios e oferece estados de carregamento, vazio e erro
Dashboard do advogado|Advogado|Organizar fila atribuída e pendências|Filtro respeita atribuição; urgência usa datas informadas; caso não atribuído não pode ser consultado
Geração de procuração|Advogado|Gerar PDF a partir de modelo aprovado e dados do caso|Documento referencia versão do modelo; campos obrigatórios ausentes impedem geração
Assinatura de procuração|Cliente|Baixar, assinar externamente e devolver procuração para conferência|Upload assinado aguarda validação do advogado; rejeição justificada permite novo envio; não presume validade automática
Timeline do caso|Usuário autorizado|Consultar histórico ordenado de eventos permitidos|Eventos persistem com autor e horário; nota interna nunca aparece na visão do cliente
Notificações internas|Usuário|Receber e marcar avisos como lidos|Mudança relevante gera um aviso por destinatário; leitura só altera a notificação do próprio usuário
E-mails transacionais|Usuário|Receber avisos e links para ações dentro da plataforma|Reenvio é limitado e deduplicado; e-mail não leva documentos nem conteúdo sensível do caso
Mensagens do caso|Cliente e advogado|Trocar mensagens assíncronas e registrar notas internas|Destinatários respeitam o caso; nota interna é omitida do cliente; texto não executa HTML ou scripts
Peças jurídicas|Advogado|Cadastrar e versionar minutas vinculadas ao caso|Minuta é interna; versões preservadas; criação exige atribuição ativa
Revisão e entrega|Advogado|Revisar e publicar versão final de defesa, petição inicial ou outra peça do caso|Só versão explicitamente revisada fica disponível ao cliente; revisão registra autor, data e versão; publicação não encerra acompanhamento judicial
Registro de protocolo|Advogado|Registrar manualmente protocolo externo e comprovante|Registro exige órgão, identificador, data e comprovante; sistema não afirma ter protocolado automaticamente
Movimentações|Advogado|Registrar andamento externo manualmente|Registro informa fonte e data do evento, separadas da data de cadastro; cliente vê apenas conteúdo publicável
Prazos informados|Advogado|Cadastrar vencimento, responsável e lembretes|Data é confirmada pelo advogado; sistema não calcula prazo processual; alteração mantém histórico
Categorias e modelos|Administrador|Gerenciar categorias atendidas e modelos aprovados|Categoria inativa não aceita novos casos; modelos antigos seguem referenciados nas procurações emitidas
Administração de usuários|Administrador|Pesquisar contas e controlar seus papéis e bloqueios|Elevação de privilégio exige autenticação reforçada e auditoria; não permite remover último administrador ativo
Administração de assinatura|Administrador|Consultar pedidos e conciliar cancelamentos e estornos|Estado financeiro vem do provedor; toda intervenção tem motivo; não é possível marcar pagamento pago sem evidência
Auditoria|Administrador autorizado|Investigar ações críticas e acessos a documentos|Consulta é filtrada e paginada; eventos não são editáveis pela interface; dados de cartão e segredos não aparecem
Solicitações de privacidade|Cliente|Solicitar acesso, correção, exportação ou eliminação de dados|Pedido autenticado recebe protocolo e acompanhamento; retenção impeditiva exige justificativa e resposta
Termos e privacidade|Cliente|Consultar políticas e registrar ciência ou aceite aplicável|Documento tem versão e vigência; aceite registra versão, usuário e horário; não agrega consentimentos opcionais
Busca de casos|Cliente e advogado|Filtrar lista por estado, categoria e referência|Filtros mantêm escopo de acesso e paginação; resultado vazio não é erro
Encerramento de caso|Advogado|Encerrar e, se necessário, reabrir caso com justificativa|Encerramento preserva documentos; reabertura é auditada e respeita política de atendimento
Exportação do caso|Cliente|Obter cópia dos documentos publicados e histórico visível|Pacote exclui notas e minutas internas; arquivo é privado, expira e exige nova autorização no download
Cadastro de processo e partes|Advogado|Registrar processo civil, órgão, partes, posição do cliente e vínculo com o caso|Permite caso pré-ajuizamento sem número e vinculação após protocolo; cliente autor e réu possuem fluxos próprios; dados de terceiros permanecem privados
Agenda de audiências|Advogado|Registrar audiências, responsável, local ou link privado, remarcações e resultado|Choque de agenda do responsável gera alerta; remarcação invalida lembretes antigos; acesso ao link e aos documentos exige vínculo ao caso
Plano de atuação por caso|Advogado|Definir etapas contratadas e acompanhar atos, peças e protocolos até a conclusão do escopo|Etapas têm responsável, estado, prazo informado e evidência; entrega de peça não encerra processo; fechamento exige avaliação de atos e prazos pendentes
`).map((r,i) => ({id:prefix('RF',i+1),title:r[0],actor:r[1],description:r[2],acceptance:r[3],priority:'MUST'}));
const benefits = [
 'decidir sobre a contratação com informações coerentes',
 'ter uma identidade verificada para acessar os serviços',
 'acessar minha área com segurança e encerrar o acesso quando necessário',
 'retomar o acesso sem expor minha conta',
 'interromper acessos indevidos após bloqueio ou comprometimento',
 'permitir atuação apenas de profissionais autorizados pela operação',
 'manter dados corretos para comunicação e atendimento',
 'contratar pelo valor confirmado sem expor dados do cartão à aplicação',
 'liberar atendimento apenas quando a contratação estiver confirmada',
 'entender quando posso submeter novos casos',
 'iniciar atendimento com informações suficientes e sem duplicidade',
 'identificar se o caso pode ser atendido e o que precisa ser complementado',
 'manter responsabilidade clara por cada atendimento',
 'acompanhar uma sequência de trabalho consistente e auditável',
 'resolver impedimentos sem perder o vínculo com o pedido original',
 'entregar evidências com acesso controlado',
 'corrigir arquivos preservando o histórico de versões',
 'consultar os arquivos necessários sem expor documentos a terceiros',
 'identificar rapidamente o andamento e as minhas próximas ações',
 'priorizar o trabalho sob minha responsabilidade',
 'preparar a autorização profissional a partir de um modelo aprovado',
 'viabilizar a conferência da autorização para atuação',
 'entender o que aconteceu no atendimento e quando',
 'perceber mudanças relevantes e pendências',
 'saber quando preciso retornar à plataforma',
 'esclarecer o atendimento preservando a confidencialidade das notas internas',
 'organizar a preparação da defesa e manter suas versões',
 'disponibilizar ao cliente apenas o material final conferido',
 'comprovar a atuação externa realizada pelo profissional',
 'manter o cliente informado sobre eventos externos registrados',
 'organizar vencimentos confirmados sem pressupor cálculo processual automático',
 'oferecer apenas categorias e modelos aprovados',
 'manter a equipe e os privilégios sob controle',
 'resolver ocorrências financeiras com evidência e rastreabilidade',
 'investigar ações relevantes sem alterar o histórico',
 'acompanhar o tratamento da minha solicitação sobre dados pessoais',
 'entender quais condições e políticas se aplicam à minha relação com a plataforma',
 'localizar o atendimento relevante sem acessar dados de outras pessoas',
 'registrar a conclusão do trabalho preservando a possibilidade de revisão justificada',
 'guardar uma cópia do conteúdo que tenho autorização para consultar',
 'distinguir ajuizamento de defesa e acompanhar corretamente as partes e o processo',
 'organizar compromissos judiciais sem perder remarcações ou expor acesso à audiência',
 'cumprir o trabalho assumido até a conclusão das etapas contratadas'
];
rf.forEach((r,i)=>{r.benefit=benefits[i];});
const rnf = parse(`
Isolamento e autorização|Toda operação protegida verifica identidade, portal, papel e vínculo no Django; testes cruzados entre dois clientes e dois advogados devem negar 100% dos acessos indevidos, inclusive reuso de sessão em outro portal
Proteção em trânsito e repouso|Produção usa TLS e serviços com criptografia em repouso; evidência de configuração registrada antes do lançamento
Minimização de dados|Payload, logs, rastreamento e banco da aplicação não contêm PAN, CVV, senhas ou tokens de recuperação em claro; inspeção automatizada usa valores sintéticos
Integridade de arquivos|Validar MIME real, tamanho de até 20 MiB e varredura; falha do scanner mantém quarentena; hash SHA-256 por versão
Idempotência|Repetir pedido ou evento 10 vezes produz uma única cobrança lógica e uma ativação; mesma chave com corpo distinto retorna 409
Consistência e concorrência|Estado de caso, histórico e evento de saída persistem na mesma transação; atualização com versão antiga retorna 409
Desempenho|Meta proposta: p95 de consultas internas abaixo de 800 ms com 20 usuários simultâneos e 10000 casos sintéticos; medir separadamente serviços externos e downloads
Acessibilidade|Fluxos essenciais navegáveis por teclado, foco visível, rótulos e erros associados; validação automática sem achados críticos e revisão manual a 200% de zoom
Recuperação|Metas propostas: RPO de 24h e RTO de 8h; comprovar restauração de banco e arquivos em ambiente isolado antes de produção
Disponibilidade|Meta interna proposta de 99,5% mensal, excluindo manutenção anunciada; medir checks externos a cada 5 minutos; não publicar SLA antes de validar operação
Observabilidade|Requisições e jobs têm identificador de correlação; alertas para falhas de pagamento, scanner, fila e backup; proibir dados jurídicos em telemetria
Tratamento de erro|Timeouts e erros externos retornam mensagem segura e requestId; usuário pode repetir operação sem duplicação
Ambientes|Desenvolvimento, homologação e produção usam bancos, buckets e credenciais separados; homologação usa somente dados sintéticos
Verificação contínua|Cada entrega executa lint, tipos quando aplicável, testes de regra e autorização, integração e build; falha bloqueia promoção
Compatibilidade|Validar jornadas principais em Chrome, Edge e Firefox estáveis e Safari móvel disponível; larguras mínimas de 360 px e desktop de 1440 px
Segredos e dependências|Segredos fora do Git; rotação documentada; varredura de dependências antes do lançamento sem achados críticos ou altos não tratados
Retenção verificável|Política aprovada por classe de dado, bloqueio de eliminação por retenção justificada e registro de execução; expiração de backups e exportações definida
Tarefas assíncronas|Worker com tentativas limitadas, backoff e fila de falhas; reprocessamento auditado não duplica efeitos; jobs não dependem de requisição aberta
`).map((r,i)=>({id:prefix('RNF',i+1),title:r[0],acceptance:r[1]}));
const rules = parse(`
Preço base|Preço ativo no código em 07/10/2026: R$ 699,90 anuais em 10 parcelas de R$ 69,99. Pedidos antigos preservam suas condições. Renovação automática aprovada, mas ainda não implementada; acompanhar docs/ETAPA_01_PRODUTO_CONTRATACAO.md|Preço implementado; recorrência pendente
Confirmação financeira|Acesso contratado só é ativado após confirmação confiável de pagamento pelo provedor; token ou código de transação isolado não basta|Proposto
Parcelamento|Pagamento parcelado de contratação anual não representa assinatura mensal; parcelas e juros devem coincidir com a cotação validada|Confirmado parcialmente; validar oferta
Período anual|Associação anual com renovação automática no mesmo parcelamento e possibilidade de cancelar a próxima renovação antes da cobrança, aprovada em 07/10/2026. Implementação e detalhes de calendário e falha de cobrança pendentes; preservar contratos anteriores sem consentimento recorrente|Regra aprovada; integração pendente
Uso ilimitado|Não impor limite comercial de quantidade de casos na vigência; limites técnicos de arquivo e antiabuso não alteram a promessa de uso|Confirmado na oferta; validar elegibilidade
Expiração e casos existentes|Preservar casos existentes após expiração, conforme confirmação de 07/10/2026. Novas submissões dependem de associação ativa; envio não equivale a aceite. Detalhar estorno e contestação sem encerrar trabalho automaticamente|Preservação confirmada; detalhes financeiros pendentes
Propriedade do caso|Cliente só lê e altera recursos do próprio caso dentro das ações permitidas; cliente não edita histórico nem decisões profissionais|Proposto
Acesso profissional|Advogado só acessa casos atribuídos; triagem exige atribuição prévia por administrador; visão de fila não expõe casos de colegas|Proposto
Responsável único|Cada caso tem no máximo um advogado responsável ativo; troca de responsável e justificativa são auditadas|Proposto
Transições|Mudança de estado obedece matriz do fluxo, pré-condições e controle de versão; recusas e reaberturas exigem motivo|Proposto
Arquivo confiável|Somente versão liberada pela verificação pode ser baixada ou usada como evidência; extensão sozinha não comprova formato|Proposto
Versionamento|Substituição cria nova versão imutável; exclusão operacional é lógica e não elimina retenções justificadas|Proposto
Procuração|Preparação jurídica exige procuração conferida conforme modelo e procedimento aprovados pelo responsável jurídico|Dependência EXT-02
Entrega de defesa|Somente peça revisada e explicitamente publicada é visível ao cliente; o próprio responsável pode revisar no MVP, sem exigir segundo advogado|Hipótese H-03
Protocolo externo|No MVP protocolo é realizado fora da plataforma e registrado manualmente com comprovante; registro não equivale a integração com tribunal|Hipótese H-04
Prazos|Advogado informa e confirma vencimentos; lembrete não substitui controle profissional nem calcula prazo processual automaticamente|Proposto
Separação de conteúdo|Notas internas e minutas não aparecem em telas, exportações, e-mails ou APIs do cliente|Proposto
Notificação|Falha de e-mail não desfaz mudança do caso; tentativa e falha ficam registradas para reenvio|Proposto
Auditoria íntegra|Ações críticas geram eventos persistidos; interface não permite apagar ou editar eventos; retenção segue política aprovada|Proposto
Motivação|Recusa, transferência, cancelamento, bloqueio e reabertura exigem motivo e autor; texto público é separado de justificativa interna|Proposto
Privacidade|Pedidos do titular passam por identidade e análise de retenção; não existe eliminação indiscriminada de arquivos por um clique|Dependência EXT-02
Privilégios|Cadastro público cria apenas cliente; advogado e administrador são provisionados por operação autorizada|Proposto
Pedido imutável|Preço, moeda, plano e cotação ficam vinculados ao pedido; servidor ignora total arbitrário enviado pelo navegador|Proposto
Eventos financeiros|Eventos repetidos e fora de ordem são reconciliados com estado autoritativo; falha de consulta não promove pagamento a pago|Proposto
Abrangência material do serviço|Atender multas de trânsito e direito civil em geral, excluindo apenas família e sucessões do escopo civil; consumo, imobiliário e demais matérias civis permanecem incluídos; exemplos de categorias não formam lista fechada; atuação civil inclui ajuizar, defender, protocolar e acompanhar, com aceite profissional e cobertura financeira por etapa definidos separadamente|Confirmado pelo usuário
`).map((r,i)=>({id:prefix('RN',i+1),title:r[0],description:r[1],status:r[2]}));
const phases = [
 ['0','Documentação e planejamento'],['1','Fundação técnica'],['2','Autenticação e usuários'],
 ['2A','Pagamentos e assinatura'],['3','Gestão de casos'],['4','Documentos'],['5','Dashboard do cliente'],
 ['6','Dashboard do advogado'],['7','Procurações'],['8','Timeline'],['9','Comunicação e notificações'],
 ['10','Gestão jurídica'],['11','Administração'],['12','Auditoria, segurança e privacidade'],
 ['13','Testes e estabilização'],['14','Homologação'],['15','Produção']
].map(([id,title])=>({id,title}));
// fase | título | horas | dependências técnicas (números DEV) | requisitos | escopo e conclusão verificável
const tasks = parse(`
0|Conferir inventário e riscos do código|8|-|RF-008 RF-009 RNF-003|Reproduzir revisão estática, confirmar arquivos e registrar achados com evidência; não executar cobrança
0|Validar escopo e regras com responsáveis|16|1|RF-010 RF-012 RF-022 RF-029 RN-004 RN-006 RN-013 RN-015|Registrar decisões H-01 a H-06, catálogo de trânsito/civil, fases cobertas e responsabilidade pelo protocolo no escritório com dois advogados; espera externa não conta como hora trabalhada
0|Revisar arquitetura, contratos e planejamento|16|2|RNF-001 RNF-009 RNF-013|Revisar modelo, permissões, tarefas e calendário; aprovar baseline ou registrar mudanças; concluir M0 somente com revisão
1|Preparar estrutura, configuração e verificação contínua|16|3|RNF-013 RNF-014 RNF-016|Fixar runtimes Node/Python compatíveis, revisar versões e configurar lint, testes e build em CI para frontend e backend; falha bloqueia entrega
1|Criar esquema inicial e migrações Django|24|4|RNF-006 RF-007 RF-010 RF-011|Modelar chaves e índices no Django ORM com usuário customizado definido antes da primeira migração; migrar e restaurar banco de teste sem perda
1|Configurar ambientes e armazenamento privado|16|4|RNF-002 RNF-013 RNF-016|Provisionar homologação com segredos separados e bucket privado; acesso anônimo negado
1|Criar camada de domínio, erros e autorização|16|5 6|RNF-001 RNF-012|Padronizar serializers DRF, erros, transaction.atomic, eventos/outbox e vínculo; filtrar queryset e validar criação; testes negam consulta cruzada
2|Implementar cadastro e verificação de e-mail|24|7|RF-002 RF-037 RN-022|Conectar frontend à identidade Django e componente mantido de verificação, incluindo envio mínimo de e-mail; testar duplicidade, aceite e token inválido
2|Implementar login, logout e sessões Django|24|8|RF-003 RF-005 RNF-001|Criar sessão Django persistida, expiração, rotação e revogação; proteger login por CSRF; testar logout e conta bloqueada
2|Implementar recuperação e alteração de perfil|16|9|RF-004 RF-007|Token único e temporário; invalidar sessões e revalidar novo e-mail; testar reutilização
2|Implementar convites, papéis e MFA da equipe|24|9|RF-006 RF-033 RN-022|Provisionar equipe por convite, exigir MFA privilegiado e impedir autoelevação ou remoção do último administrador
2A|Validar produto PagBank e contrato de integração|16|11|RF-008 RF-009 RN-023 RN-024|Confirmar APIs habilitadas e contrato do adaptador Python em sandbox; documentar mapeamento de estados e mecanismo de verificação de eventos
2A|Corrigir payload e validação financeira do checkout|24|12|RF-008 RNF-003 RN-003 RN-023|Retirar PAN, CVV e validade do payload interno; validar cotação no servidor; provar com dados sintéticos e inspeção de rede
2A|Persistir pedidos e idempotência de cobrança|24|13|RF-008 RNF-005 RN-023|Criar pedido vinculado ao usuário, chave idempotente e estado indeterminado em timeout; repetição não cria outra cobrança
2A|Implementar notificações e conciliação financeira|32|14|RF-009 RN-002 RN-024 RNF-005|Autenticar ou verificar eventos conforme produto confirmado; consultar provedor, tratar repetição e ordem invertida sem ativação indevida
2A|Implementar vigência e estados da assinatura|24|15|RF-010 RF-034 RN-004 RN-006|Ativar atomicamente, expirar e reconciliar cancelamento; UI distingue pendente, pago e recusado; testar limites de data
3|Implementar rascunho e submissão de caso|24|16|RF-011 RN-005 RN-007|Criar caso próprio com validação e vigência; submissão repetida não duplica e assinatura vencida é recusada
3|Implementar triagem e atribuição|24|17|RF-012 RF-013 RN-008 RN-009 RN-020 RN-025|Designar profissional, aceitar ou recusar com motivo e transferir caso; aplicar exclusão de família/sucessões e permitir demais matérias civis conforme RN-025; testar perda de acesso após transferência
3|Implementar máquina de estados e concorrência|24|18|RF-014 RF-039 RN-010 RNF-006|Aplicar matriz e versionamento otimista; conflito não grava histórico parcial; encerramento e reabertura auditados
3|Implementar pendências de documentos e informações|16|19|RF-015 RN-020|Criar, responder e resolver pendências; manter retorno ao estado anterior registrado sem permitir saltos inválidos
4|Implementar upload privado e metadados|24|20 6|RF-016 RNF-004 RN-007|Validar tamanho e formato, gerar chave privada e vincular arquivo ao caso; rejeitar upload para caso alheio
4|Implementar quarentena e verificação de arquivo|24|21|RF-016 RNF-004 RNF-018 RN-011|Integrar scanner, checksum e worker Python persistente com lease e retry; falhas não liberam download; testar retomada após encerramento do worker e fixture do scanner
4|Implementar versões e download autorizado|24|22|RF-017 RF-018 RN-012 RNF-001|Preservar versões e emitir URL curta após checagem de vínculo; URL expirada ou arquivo não liberado é recusado
5|Construir painel e busca do cliente|24|23|RF-019 RF-038 RNF-008 RNF-015|Listar casos, assinatura e pendências com paginação; testar dois clientes, teclado, vazio e erro
5|Construir detalhe e resposta a pendências|24|24|RF-011 RF-015 RF-018 RF-019|Conectar formulários e documentos no painel; validar jornada abrir caso e enviar complemento em tela pequena
6|Construir fila e filtros do advogado|24|25|RF-020 RF-038 RN-008|Exibir apenas casos atribuídos e ordenação por vencimento informado; testar filtros sem vazamento
6|Construir área de trabalho e triagem|24|26|RF-012 RF-014 RF-020|Conectar triagem, documentos e ações permitidas; testar transferência e bloqueio de ações inválidas
7|Implementar modelo versionado e geração de procuração|24|27|RF-021 RF-032 RN-013|Gerar PDF com campos validados, armazenar versão do modelo e hash; validar amostra com responsável jurídico
7|Implementar devolução assinada e conferência|24|28|RF-022 RN-013|Cliente envia arquivo assinado; advogado aprova ou rejeita com motivo; assinatura externa não é validada automaticamente
8|Publicar timeline a partir dos eventos persistidos|16|29 19|RF-023 RN-017 RNF-006|Expor histórico paginado e filtrado por público; eventos anteriores à tela também aparecem sem duplicar
9|Implementar mensagens e notas internas|24|30|RF-026 RN-017|Criar conversa por caso e notas restritas; testar API, UI e exportação contra exposição interna e XSS
9|Consolidar outbox e implementar notificações internas|24|31 22|RF-024 RNF-018 RN-018|Expandir consumidor existente para avisos com retry e deduplicação; leitura e destinatário respeitam autorização
9|Implementar e-mails e modelos transacionais|24|32|RF-025 RNF-003 RN-018|Enviar links seguros e genéricos; capturar falhas e bounces; testar duplicação e indisponibilidade do provedor
10|Implementar peças e revisão para publicação|32|33|RF-027 RF-028 RN-014|Manter minutas privadas e publicar versão revisada; verificar que cliente nunca consulta minuta
10|Implementar registro de protocolo e movimentações|24|34|RF-029 RF-030 RN-015|Registrar fonte, data e comprovante privado; validar campos e separar data do evento da data de registro
10|Implementar prazos e lembretes|24|35|RF-031 RN-016 RNF-018|Cadastrar vencimento confirmado, responsável e alertas; editar ou concluir prazo invalida lembretes obsoletos
10|Implementar encerramento e exportação do caso|24|36|RF-039 RF-040 RN-006 RN-017|Encerrar com motivo e gerar pacote privado com expiração; excluir minutas e notas internas da exportação
11|Construir gestão de usuários e atribuições|24|37 11|RF-013 RF-033 RN-009 RN-022|Administração usa serviços Django com MFA, auditoria e concessão por aprovador distinto; testar último administrador, expiração e revogação; restringir Django Admin para não contornar domínio
11|Construir gestão de categorias e modelos|16|38|RF-032 RF-021 RN-025|Organizar catálogo civil conforme RN-025 sem limitá-lo aos exemplos; família/sucessões fora da oferta; inativar sem quebrar histórico; nova versão de modelo não altera documentos emitidos
11|Construir consulta financeira e intervenção controlada|24|39 16|RF-034 RF-010 RN-024|Consultar pedidos, eventos e conciliação; solicitar estorno por fluxo confirmado do provedor; gravar evidência e motivo
12|Consolidar auditoria e revisão de acesso|24|40|RF-035 RN-019 RNF-001|Auditar ações e downloads; limitar consulta administrativa e testar ausência de segredos; revisar todos os endpoints
12|Implementar solicitações de privacidade e retenção|32|41|RF-036 RN-021 RNF-017|Registrar pedido, confirmar identidade, exportar ou eliminar sob política aprovada; testar retenção impeditiva e expiração de exportação
12|Publicar políticas e revisar comunicação institucional|16|42|RF-001 RF-037 RN-001 RNF-008|Publicar textos aprovados e aceite versionado; substituir ou retirar depoimentos fictícios e links vazios
12|Revisar segurança, segredos e minimização|24|43|RNF-002 RNF-003 RNF-016|Revisar ameaças, dependências, cookies, headers e payload; tratar achados e comprovar ausência de cartão em logs
13|Executar regressão de regras e isolamento|24|44|RNF-001 RNF-005 RNF-006 RNF-014|Executar matriz de casos positivos, negativos e concorrentes; registrar resultados e corrigir defeitos conhecidos dentro do escopo
13|Executar jornada E2E e testes de falhas externas|32|45|RF-008 RF-009 RF-022 RF-028 RNF-012 RNF-018|Cobrir contratação até entrega, timeout financeiro, evento repetido, falha de scanner e retry de e-mail com sandbox e fixtures
13|Verificar desempenho, acessibilidade e navegadores|24|46|RNF-007 RNF-008 RNF-015|Medir metas com massa sintética e registrar ambiente; corrigir impedimentos nas jornadas principais
13|Ensaiar restauração e resposta a incidente|24|47|RNF-009 RNF-010 RNF-011 RNF-017|Restaurar banco e objetos em isolamento, medir RPO/RTO e simular incidente sem dados reais; registrar evidências
14|Preparar roteiro e massa para homologação|16|48|RNF-014 RF-012 RF-028|Criar contas e casos sintéticos para todos os papéis, roteiro e lista de critérios; agendar avaliadores externos
14|Acompanhar homologação funcional e operacional|24|49|RF-010 RF-022 RF-029 RF-036|Executar roteiro com responsáveis, registrar aceite ou defeitos; tempo de espera por avaliadores não é hora do programador
14|Corrigir itens de aceite e fechar homologação|24|50|RNF-014 RNF-001|Resolver defeitos esperados de aceite e repetir cenários afetados; nenhum bloqueador aberto; obter decisão documentada
15|Preparar produção, alertas e backups|24|51|RNF-002 RNF-009 RNF-010 RNF-011 RNF-013 RNF-016|Configurar produção isolada, segredos, domínio, monitoração e backups; verificar restauração e contatos operacionais
15|Executar implantação controlada e reversão ensaiada|16|52|RNF-014 RNF-012|Migrar com cópia de segurança, implantar e executar smoke tests; demonstrar reversão compatível sem repetir cobranças
15|Validar operação assistida e entregar runbook|16|53|RNF-010 RNF-011 RNF-018|Acompanhar fila, conciliação e alertas durante janela assistida; registrar responsável pela continuidade e pendências sem bloqueadores
`).map((r,i)=>({id:prefix('DEV',i+1),phase:r[0],title:r[1],hours:Number(r[2]),dependencies:r[3]==='-'?[]:r[3].split(' ').map(n=>prefix('DEV',Number(n))),requirements:r[4].split(' '),acceptance:r[5],priority:'MUST',status:'Planejado'}));
const config = {
 documentVersion:'1.5',
 architectureNote:'Arquitetura aprovada: Next.js + TypeScript no frontend, Python + Django REST Framework no backend, PostgreSQL e worker Python separado. DEV-059 a DEV-064 acrescentam 80h técnicas para integração, isolamento dos portais e operação; reserva recalculada por fase.',
 baselineDate:'2026-09-16', startDate:'2026-09-16', hoursPerDay:8, hoursPerWeek:40,
 developers:1, contingencyRate:0.20,
 // Datas sem expediente confirmadas pelo responsável devem ser incluídas aqui e o cronograma regenerado.
 nonWorkingDates:[],
 calendarNote:'Calendário provisório de segunda a sexta-feira; feriados, férias e ausências ainda não descontados. As datas dependem da confirmação do calendário e das dependências externas.',
 milestones:[['M0','Documentação revisada','0'],['M1','Fundação funcionando','1'],['M2','Autenticação funcionando','2'],['M3','Cliente consegue abrir caso','5'],['M4','Advogado recebe e trabalha no caso','6'],['M5','Procuração funcionando','7'],['M6','Acompanhamento completo','9'],['M7','Fluxo jurídico completo','10'],['M8','MVP Feature Complete','12'],['M9','Homologação concluída','14'],['M10','Produção validada','15']]
};
// Extensões confirmadas: atuação civil completa e arquitetura Django/Next.js. IDs anteriores permanecem estáveis.
const additions = [
 {after:'DEV-017',id:'DEV-055',phase:'3',title:'Cadastrar processos, partes e posição do cliente',hours:24,dependencies:['DEV-017'],requirements:['RF-041','RNF-001'],acceptance:'Implementar caso civil como autor ou réu, partes privadas, órgão e número opcional antes de ajuizar; testar vínculo após protocolo e acesso cruzado'},
 {after:'DEV-036',id:'DEV-056',phase:'10',title:'Implementar agenda de audiências e remarcações',hours:24,dependencies:['DEV-036','DEV-055'],requirements:['RF-042','RF-031','RNF-018'],acceptance:'Registrar audiência, responsável, local/link privado e resultado; avisar sobre choque de agenda e invalidar lembrete anterior ao remarcar'},
 {after:'DEV-056',id:'DEV-057',phase:'10',title:'Implementar etapas contratadas e ciclo judicial',hours:16,dependencies:['DEV-056'],requirements:['RF-043','RF-028','RF-029','RF-039'],acceptance:'Relacionar petição inicial, defesa e demais atos às etapas contratadas; publicação não encerra acompanhamento; impedir fechamento com ato bloqueante ou prazo pendente'},
 {after:'DEV-046',id:'DEV-058',phase:'13',title:'Validar jornadas judiciais como autor e réu',hours:16,dependencies:['DEV-046','DEV-057'],requirements:['RF-041','RF-042','RF-043','RNF-014'],acceptance:'Testar ajuizamento e defesa, cadastro de protocolo externo, remarcação de audiência, peça posterior e encerramento somente após revisão das pendências'},
 {after:'DEV-004',id:'DEV-059',phase:'1',title:'Preparar backend Django e contrato DRF',hours:16,dependencies:['DEV-004'],requirements:['RNF-013','RNF-014','RNF-016'],acceptance:'Criar base backend, settings separados, dependências travadas, usuário customizado e esquema OpenAPI; comprovar inicialização/testes sem alterar a landing'},
 {after:'DEV-006',id:'DEV-060',phase:'1',title:'Configurar entrada HTTPS e API por portal',hours:16,dependencies:['DEV-006','DEV-059'],requirements:['RNF-001','RNF-002','RNF-013'],acceptance:'Encaminhar /api/v1 dos portais ao Django e telas ao Next.js; validar hosts, remover headers forjados e impedir acesso direto não confiável à origem'},
 {after:'DEV-009',id:'DEV-061',phase:'2',title:'Integrar frontend e sessões isoladas por portal',hours:16,dependencies:['DEV-009','DEV-060'],requirements:['RF-003','RF-005','RNF-001'],acceptance:'Conectar cliente HTTP TypeScript a sessão Django e CSRF; negar cookie copiado para outro portal, desabilitar cache privado compartilhado e validar renovação do token após login'},
 {after:'DEV-013',id:'DEV-062',phase:'2A',title:'Migrar checkout para API Django e retirar rotas legadas',hours:8,dependencies:['DEV-013','DEV-061'],requirements:['RF-008','RF-009','RNF-003'],acceptance:'Apontar frontend ao adaptador Django, manter payload mínimo e remover execução financeira das rotas Next.js; testes impedem cobrança por endpoint antigo'},
 {after:'DEV-045',id:'DEV-063',phase:'13',title:'Testar fronteiras Next.js, Django e portais',hours:16,dependencies:['DEV-045','DEV-061','DEV-062'],requirements:['RNF-001','RNF-013','RNF-014'],acceptance:'Validar CSRF no login, header de host forjado, sessão copiada, MFA pendente, cache privado, listagens/criação DRF e tentativas de contornar regras pelo Django Admin'},
 {after:'DEV-052',id:'DEV-064',phase:'15',title:'Validar implantação coordenada de frontend, API e worker',hours:8,dependencies:['DEV-052','DEV-063'],requirements:['RNF-011','RNF-013','RNF-016'],acceptance:'Conferir artefatos e health checks de três processos, migração única Django, segredos somente no backend e compatibilidade para reversão coordenada'}
];
for(const {after,...task} of additions) tasks.splice(tasks.findIndex(t=>t.id===after)+1,0,{...task,priority:'MUST',status:'Planejado'});
tasks.find(t=>t.id==='DEV-018').dependencies.push('DEV-055');
tasks.find(t=>t.id==='DEV-037').dependencies.push('DEV-057');
tasks.find(t=>t.id==='DEV-047').dependencies.push('DEV-058');
tasks.find(t=>t.id==='DEV-005').dependencies.push('DEV-059');
tasks.find(t=>t.id==='DEV-007').dependencies.push('DEV-060');
tasks.find(t=>t.id==='DEV-010').dependencies.push('DEV-061');
tasks.find(t=>t.id==='DEV-014').dependencies.push('DEV-062');
tasks.find(t=>t.id==='DEV-046').dependencies.push('DEV-063');
tasks.find(t=>t.id==='DEV-053').dependencies.push('DEV-064');
for (const [id, status] of Object.entries({
 'DEV-020': 'Implementado localmente: complemento com anexos',
 'DEV-021': 'Implementado localmente; armazenamento produtivo pendente',
 'DEV-022': 'Implementado; homologação do scanner real pendente',
 'DEV-023': 'Validado localmente; aceite produtivo pendente',
})) {
 const task = tasks.find(t => t.id === id);
 task.status = status;
 task.evidence = '[Documentos privados](DOCUMENTOS.md): testes locais em 21/09/2026; não representa aceite produtivo';
}
module.exports = {rf,rnf,rules,phases,tasks,config};
