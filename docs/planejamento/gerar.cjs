const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {rf,rnf,rules,phases,tasks,config} = require('./dados.cjs');
const root = path.resolve(__dirname, '../..');
const check = process.argv.includes('--check');
const fmt = n => String(Number(n.toFixed(2))).replace('.', ',');
const date = s => new Date(`${s}T00:00:00Z`);
const iso = d => d.toISOString().slice(0,10);
const br = s => s.split('-').reverse().join('/');
const next = d => {const result = new Date(d); result.setUTCDate(result.getUTCDate()+1); return result;};
const off = new Set(config.nonWorkingDates);
const working = d => ![0,6].includes(d.getUTCDay()) && !off.has(iso(d));
assert.equal(config.developers,1);
assert.equal(config.hoursPerDay,8);
assert.equal(config.hoursPerWeek,40);
assert.equal(iso(date(config.startDate)),config.startDate);
for (const d of off) assert.equal(iso(date(d)),d);
assert(config.contingencyRate >= 0);
const ids = new Set([...rf,...rnf,...rules,...tasks].map(x=>x.id));
assert.equal(ids.size,rf.length+rnf.length+rules.length+tasks.length);
const requirementIds = new Set([...rf,...rnf,...rules].map(x=>x.id));
const done = new Set();
let lastPhase = -1;
for (const task of tasks) {
  assert(task.hours > 0 && task.hours % 8 === 0,task.id);
  assert(phases.some(p=>p.id===task.phase),task.id);
  const phaseIndex = phases.findIndex(p=>p.id===task.phase);
  assert(phaseIndex >= lastPhase,`${task.id}: fase fora de ordem`); lastPhase=phaseIndex;
  task.dependencies.forEach(dep=>assert(done.has(dep),`${task.id}: dependência não anterior ${dep}`));
  task.requirements.forEach(id=>assert(requirementIds.has(id),`${task.id}: requisito desconhecido ${id}`));
  done.add(task.id);
}
for (const req of [...rf,...rnf,...rules]) assert(tasks.some(t=>t.requirements.includes(req.id)),`Sem tarefa: ${req.id}`);
let cursor=date(config.startDate), accumulated=0;
const intervals=[];
function allocate(hours, id, title, kind, phase) {
  while (!working(cursor)) cursor=next(cursor);
  const start=iso(cursor);
  let remaining=hours;
  while (remaining>0) {if (working(cursor)) remaining-=8; if (remaining>0) cursor=next(cursor);}
  const end=iso(cursor); cursor=next(cursor); accumulated+=hours;
  const entry={id,title,kind,phase,hours,start,end,cumulative:accumulated};
  intervals.push(entry); return entry;
}
const schedule=phases.map(p=>{
  const items=tasks.filter(t=>t.phase===p.id);
  const hours=items.reduce((s,t)=>s+t.hours,0);
  const contingency=Math.ceil(hours*config.contingencyRate/8)*8;
  const allocations=items.map(t=>allocate(t.hours,t.id,t.title,'Tarefa',p.id));
  const reserve=allocate(contingency,`RES-${p.id}`,`Reserva da fase ${p.id}`,'Contingência',p.id);
  return {...p,hours,contingency,total:hours+contingency,start:allocations[0].start,end:reserve.end,cumulative:accumulated,allocations,reserve};
});
const technical=tasks.reduce((s,t)=>s+t.hours,0);
const contingency=schedule.reduce((s,p)=>s+p.contingency,0);
const total=technical+contingency;
assert.equal(total,accumulated);
for(let i=1;i<intervals.length;i++) assert(intervals[i].start>intervals[i-1].end,'Sobreposição');
const milestones=config.milestones.map(([id,title,phase])=>({...schedule.find(p=>p.id===phase),id,title,phase}));
const m = id => milestones.find(x=>x.id===id);
const metadata=`> Revisão ${config.documentVersion} · Base: ${br(config.baselineDate)} · Arquitetura aprovada; validação operacional pendente.\n`;
const table = (headers,rows)=>`| ${headers.join(' | ')} |\n| ${headers.map(()=> '---').join(' | ')} |\n${rows.map(r=>`| ${r.join(' | ')} |`).join('\n')}\n`;
const output = new Map();
function doc(file,title,body){output.set(`docs/${file}`,`# ${title}\n\n${metadata}\n${body.trim()}\n`);}
doc('REQUISITOS_FUNCIONAIS.md','Requisitos funcionais',`
Catálogo de ${rf.length} requisitos do MVP proposto. MUST significa necessário para o escopo desta baseline, e não funcionalidade já implementada. A evidência atual está em [Estado atual](ESTADO_ATUAL.md). Os critérios abaixo devem ser testados; as evidências do primeiro incremento de acesso estão em [Acesso local](ACESSO.md), sem aceite integral do MVP.

Origem: proposta comercial e fluxos existentes no repositório, diretrizes fornecidas e detalhamento de engenharia. A lista constitui proposta a validar, não relato de entrevistas já realizadas. Regras e hipóteses em [Regras de negócio](REGRAS_DE_NEGOCIO.md) e [Decisões](DECISOES.md).

${rf.map(r=>`## ${r.id} — ${r.title}\n\n**Ator:** ${r.actor}. **Prioridade:** ${r.priority}.\n\n${r.description}.\n\n**Critério de aceite:** ${r.acceptance}.\n\n**Rastreabilidade:** US-${r.id.slice(3)}; ${tasks.filter(t=>t.requirements.includes(r.id)).map(t=>t.id).join(', ')}.`).join('\n\n')}
`);
doc('REQUISITOS_NAO_FUNCIONAIS.md','Requisitos não funcionais',`
${rnf.length} metas propostas, ainda não medidas nem certificadas. Cada requisito tem tarefa associada em [Rastreabilidade](RASTREABILIDADE.md). Desempenho, disponibilidade e recuperação dependem da infraestrutura contratada e da capacidade operacional; não são promessas comerciais.

${rnf.map(r=>`## ${r.id} — ${r.title}\n\n${r.acceptance}.`).join('\n\n')}
`);
doc('REGRAS_DE_NEGOCIO.md','Regras de negócio',`
${rules.length} regras. As regras confirmadas indicam evidência no produto atual ou decisão explícita do usuário, conforme a situação registrada; hipóteses e decisões propostas precisam de validação conforme [Decisões](DECISOES.md). Não representam aprovação jurídica do serviço.

${rules.map(r=>`## ${r.id} — ${r.title}\n\n${r.description}.\n\n**Situação:** ${r.status}.`).join('\n\n')}
`);
doc('USER_STORIES.md','User stories',`
${rf.length} histórias correspondentes aos requisitos funcionais. Cada história herda a prioridade MUST do requisito e possui aceite observável. Para fluxos combinados, consultar [Casos de uso](CASOS_DE_USO.md).

${rf.map(r=>`## US-${r.id.slice(3)} — ${r.title}\n\nComo **${r.actor.toLowerCase()}**, preciso **${r.description.charAt(0).toLowerCase()+r.description.slice(1)}**, para **${r.benefit}**.\n\n**Aceite:** ${r.acceptance}.\n\n**Requisito:** ${r.id}. **Tarefas:** ${tasks.filter(t=>t.requirements.includes(r.id)).map(t=>t.id).join(', ')}.`).join('\n\n')}
`);
doc('BACKLOG.md','Backlog executável',`
${tasks.length} tarefas, ${technical} horas técnicas. Toda tarefa tem prioridade MUST nesta baseline; funcionalidades posteriores estão explicitamente excluídas em [MVP](MVP.md). Os estados distinguem planejamento e incrementos locais; não significam aceite produtivo. Para acesso e casos, consulte também [Estado atual](ESTADO_ATUAL.md). A fase 0 estima a conferência e validação humana, não contabiliza retroativamente o tempo desta sessão.

${config.architectureNote} Acesso local possui evidências em [Acesso local](ACESSO.md). Contrato OpenAPI, domínios reais e operação produtiva ainda não foram concluídos.

**Ordem de execução:** a sequência abaixo é estritamente serial, com um desenvolvedor. Dependências técnicas são indicadas por tarefa; a tarefa anterior na lista é também predecessora por capacidade. Cada fase tem reserva separada em [Cronograma](CRONOGRAMA.md). Não executar tarefas automaticamente a partir deste documento: esta entrega é de planejamento; implementação começa após autorização.

**Estimativa:** julgamento de engenharia a partir do inventário e dos critérios abaixo; confiança média-baixa até validar fornecedores e regras. Inclui implementação, testes locais de regra/autorização e revisão de cada entrega. A fase 13 cobre regressão transversal e ensaios; fase 14 cobre aceite e correções esperadas. Contingência cobre desvios não previstos, sem duplicar esses esforços. Reestimar após fase 0 e após homologar pagamento. Espera por terceiros é atraso de calendário, não horas técnicas.

**Definition of Ready:** decisão funcional disponível, contrato e permissão identificados, dados sintéticos e dependências prontas. **Definition of Done:** aceite atendido, testes pertinentes passando, documentação atualizada, revisão de segurança aplicável e evidência vinculada. Sem isso, a tarefa não está concluída.

${table(['ID','Fase','Atividade','Horas','Dependências técnicas','Prioridade'],tasks.map(t=>[t.id,t.phase,t.title,t.hours,t.dependencies.join(', ')||'—',t.priority]))}

${tasks.map((t,i)=>`## ${t.id} — ${t.title}\n\n- **Fase:** ${t.phase} — ${phases.find(p=>p.id===t.phase).title}.\n- **Prioridade / estado:** ${t.priority} / ${t.status}.\n- **Estimativa:** ${t.hours}h (${t.hours/8} dias de capacidade).\n- **Dependências técnicas:** ${t.dependencies.join(', ')||'nenhuma'}.\n- **Predecessora por capacidade:** ${i?tasks[i-1].id:'nenhuma'}.\n- **Requisitos relacionados:** ${t.requirements.join(', ')}.\n- **Descrição e critério de conclusão:** ${t.acceptance}.\n- **Evidência:** ${t.evidence || "demonstração do cenário descrito, resultado das verificações aplicáveis e referência da entrega; pendente de execução"}.`).join('\n\n')}
`);
const summary = `**Início de referência:** ${br(config.startDate)}\n\n**Desenvolvedor:** 1 · **Carga:** 8h/dia · **Carga semanal:** 40h\n\n**Horas técnicas planejadas:** ${technical}h\n\n**Contingência:** ${contingency}h (${fmt(contingency/technical*100)}% efetivos)\n\n**Total:** ${total}h · **Dias de capacidade:** ${total/8} · **Semanas de capacidade:** ${fmt(total/40)}\n\n**MVP Feature Complete:** ${br(m('M8').end)}\n\n**Homologação concluída:** ${br(m('M9').end)}\n\n**Produção validada:** ${br(m('M10').end)}`;
doc('CRONOGRAMA.md','Cronograma e previsão do MVP',`
## Previsão do projeto

${config.architectureNote}

${summary}

**Datas condicionais, não compromisso de entrega.** ${config.calendarNote} A data inicial é a data desta documentação, não uma declaração de que o desenvolvimento começou. Se o início real mudar, atualizar a configuração e recalcular antes de usar as datas. Aprovações externas podem deslocar os marcos além da reserva.

## Método e calendário

1. Somar as estimativas individuais do [Backlog](BACKLOG.md), sem paralelismo entre tarefas.
2. Reservar 20% por fase, arredondados para o próximo dia de 8h. Por isso a reserva efetiva supera 20%; o arredondamento fica visível na tabela.
3. Alocar tarefas e reserva em dias inteiros; o primeiro dia trabalhado conta como dia 1. Data final é inclusiva; na coluna Mermaid, término é exclusivo para renderizar o último dia.
4. Trabalhar de segunda a sexta, 8h/dia; não assumir QA, designer, DevOps ou especialista separado. Horas técnicas incluem documentação/revisão, desenvolvimento, configuração, testes e implantação.
5. Feriados, férias e ausências: lista **nonWorkingDates** inicialmente vazia, pois local e calendário do desenvolvedor não foram confirmados. Não interpretar a previsão como calendário nacional homologado. Informar cada dia sem expediente em ISO e regenerar. Horas/8 são dias de capacidade; semanas/40 não são semanas corridas.
6. Reservas aparecem após cada fase para tornar a previsão conservadora. Só consumir por desvio registrado; não criar funcionalidade extra para preencher reserva. Ganhos e desvios exigem revisão da baseline.

## Fases e reservas

${table(['Fase','Entrega','Técnicas h','Reserva h','Total h','Início','Fim com reserva'],schedule.map(p=>[p.id,p.title,p.hours,p.contingency,p.total,br(p.start),br(p.end)]))}

**Totais:** ${technical}h técnicas + ${contingency}h de contingência = ${total}h. A fase 2A explicita pagamentos e assinatura sem renumerar as fases 0–15 das diretrizes originais.

## Marcos e critérios

As datas incluem todas as tarefas e reservas acumuladas até o final da fase indicada. M0 significa revisão aceita da documentação, não só arquivos criados. M8 significa escopo implementado; regressão, homologação e publicação continuam depois dele.

${table(['Marco','Resultado','Até fase','Horas acumuladas','Dias acumulados','Data prevista'],milestones.map(p=>[p.id,p.title,p.id==='M0'?'0':config.milestones.find(x=>x[0]===p.id)?.[2]||p.id,p.cumulative,p.cumulative/8,br(p.end)]))}

Critérios de passagem: M1 ambientes/migrações verificáveis; M2 cadastro, sessão e papéis; M3 assinatura, abertura e documentos no painel; M4 triagem e fila profissional; M5 geração e conferência de procuração; M6 timeline, mensagens e avisos; M7 peça revisada, protocolo manual e prazos; M8 administração e privacidade completas; M9 roteiro aprovado e sem bloqueadores; M10 implantação, restauração e monitoramento verificados. Relacionar evidências de execução a cada marco quando ocorrer.

## Roadmap visual

As barras técnicas e de reserva são separadas. Toda linha depende do término da anterior por capacidade do único desenvolvedor; dependências técnicas específicas estão no backlog. As datas explícitas evitam divergência entre o Gantt e o cálculo.

\`\`\`mermaid
gantt
    title Iustus — um desenvolvedor, datas condicionais
    dateFormat YYYY-MM-DD
    axisFormat %d/%m/%Y
    excludes weekends${off.size?', '+[...off].join(', '):''}
${schedule.map((p,i)=>`    section Fase ${p.id} — ${p.title}\n    Trabalho técnico :f${i}, ${p.start}, ${iso(next(date(p.allocations.at(-1).end)))}\n    Reserva ${p.contingency}h :r${i}, ${p.reserve.start}, ${iso(next(date(p.reserve.end)))}`).join('\n')}
\`\`\`

## Alocação por tarefa

${table(['Item','Fase','Horas','Início','Fim','Horas acumuladas'],intervals.map(x=>[x.id,x.phase,x.hours,br(x.start),br(x.end),x.cumulative]))}

## Dependências externas e atualização

EXT-01 a EXT-06 estão em [Decisões](DECISOES.md); esperar por validação jurídica, conta PagBank ou infraestrutura não consome horas do programador. Se uma dependência não estiver pronta no marco necessário, pausar a tarefa e recalcular; não presumir chegada automática do insumo.

Fonte única: [dados.cjs](planejamento/dados.cjs). Regerar com **node docs/planejamento/gerar.cjs**; verificar sem escrever com **node docs/planejamento/gerar.cjs --check**. Atualizar **startDate**, ausências, estimativas e dependências na fonte, nunca só uma data no README. **baselineDate** permanece como data do levantamento; uma revisão aprovada deve atualizar a versão documental. O comando também valida cobertura dos requisitos, referências, somas e ausência de sobreposição.
`);
doc('RASTREABILIDADE.md','Matriz de rastreabilidade',`
Esta matriz demonstra cobertura planejada, não validação concluída. Cada requisito funcional tem uma história e pelo menos uma tarefa; requisitos não funcionais e regras têm tarefas associadas. Critérios de verificação constam dos catálogos e de [Testes](TESTES.md).

${table(['Requisito','História','Tarefas','Fases','Situação'],[...rf,...rnf,...rules].map(r=>{const ts=tasks.filter(t=>t.requirements.includes(r.id));return [r.id,r.id.startsWith('RF-')?`US-${r.id.slice(3)}`:'—',ts.map(t=>t.id).join(', '),[...new Set(ts.map(t=>t.phase))].join(', '),'Planejado; não testado'];}))}
`);
doc('PLANO_DE_COMMITS.md','Plano de commits',`
Cada tarefa pode exigir mais de um commit. Os títulos abaixo definem a unidade de entrega; separar migração, domínio e interface quando cada parte puder ser verificada independentemente. Nunca juntar tarefas não relacionadas nem deixar migração incompatível com o código da mesma entrega.

Antes de cada commit: revisar diff, remover segredos/dados reais, executar verificações pertinentes e atualizar evidência do aceite. Não criar commits nesta etapa automaticamente.

${table(['Tarefa','Título proposto','Verificação'],tasks.map(t=>[t.id,`${t.phase==='0'?'docs':t.phase==='13'||t.phase==='14'?'test':t.phase==='15'?'chore':'feat'}(${t.phase==='2A'?'billing':({0:'planning',1:'foundation',2:'auth',3:'cases',4:'documents',5:'client',6:'lawyer',7:'mandates',8:'timeline',9:'notifications',10:'legal',11:'admin',12:'security',13:'quality',14:'acceptance',15:'release'})[t.phase]}): ${t.title.charAt(0).toLowerCase()+t.title.slice(1)}`,`Critério de ${t.id} e Definition of Done`]))}
`);
doc('RESUMO_EXECUTIVO.md','Resumo executivo do planejamento',`
**Situação:** acesso, casos/triagem e documentos privados implementados localmente. Scanner real e armazenamento produtivo aguardam homologação. Baseline e hipóteses operacionais aguardam validação. As horas abaixo representam a estimativa integral, não o saldo restante.

Stack atual: Next.js 15.5.25, React 19.1.9 e TypeScript incremental; Django 5.2.17 e DRF 3.18.1 com PostgreSQL, cadastro, sessões por portal, MFA e worker de e-mails de identidade. PagBank permanece no legado Next.js; casos possuem rascunho, atribuição e triagem. Arquivos e elegibilidade financeira continuam pendentes.

${config.architectureNote} A integração dos portais foi testada localmente. Contrato OpenAPI, subdomínios reais e operação produtiva ainda não foram concluídos.

- Requisitos funcionais: ${rf.length}.
- Requisitos não funcionais: ${rnf.length}.
- Regras de negócio: ${rules.length}.
- User stories: ${rf.length}.
- Tarefas do backlog: ${tasks.length}.

${summary}

${config.calendarNote}

**Próxima tarefa recomendada:** pagamentos e assinatura, iniciando por DEV-012/013. O incremento de [documentos privados](DOCUMENTOS.md) está implementado localmente; scanner real e armazenamento produtivo aguardam homologação. Antes de cobrança/publicação, corrigir o checkout e homologar dependências produtivas. Os testes locais não significam aceite integral dos requisitos nem aprovação operacional.
`);
// Sincronizar apenas bloco gerado do README; conteúdo editorial permanece intacto.
const readmePath = path.join(root,'README.md');
if(fs.existsSync(readmePath)) {
 const original=fs.readFileSync(readmePath,'utf8');
 const start='<!-- PLANEJAMENTO:INICIO -->',end='<!-- PLANEJAMENTO:FIM -->';
 assert(original.includes(start)&&original.includes(end),'README sem marcadores de planejamento');
 const a=original.indexOf(start),b=original.indexOf(end)+end.length;
 output.set('README.md',original.slice(0,a)+start+'\n\n'+summary+'\n\n'+config.calendarNote+' Detalhamento, reservas e dependências: [Cronograma](docs/CRONOGRAMA.md).\n\n'+end+original.slice(b));
}
for(const [file,content] of output){
 const full=path.join(root,file);
 if(check) assert.equal(fs.readFileSync(full,'utf8').replace(/\r\n/g,'\n'),content.replace(/\r\n/g,'\n'),`${file} desatualizado`);
 else fs.writeFileSync(full,content,'utf8');
}
console.log(check?'PLANEJAMENTO VERIFICADO':`DOCUMENTAÇÃO IUSTUS — revisão ${config.documentVersion}; validação operacional pendente`);
console.log(`Stack: Next.js 15.5.25 / React 19.1.9 / Django / PostgreSQL`);
console.log(config.architectureNote);
console.log(`RF: ${rf.length}; RNF: ${rnf.length}; RN: ${rules.length}; US: ${rf.length}; tarefas: ${tasks.length}`);
console.log(`Horas técnicas: ${technical}; contingência: ${contingency}; total: ${total}; dias: ${total/8}; semanas: ${fmt(total/40)}`);
console.log(`MVP: ${br(m('M8').end)}; homologação: ${br(m('M9').end)}; produção: ${br(m('M10').end)}`);
console.log(config.calendarNote);
console.log('Próxima tarefa: pagamentos e assinatura (DEV-012/013). Documentos locais implementados; scanner real, armazenamento produtivo e produção pendentes.');
