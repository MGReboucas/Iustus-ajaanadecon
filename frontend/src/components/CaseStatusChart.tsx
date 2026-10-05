type StateCount = { id: string; count: number };
const groups = [
  { label: "Rascunhos", states: ["RASCUNHO"], color: "#8492a6" },
  { label: "Em análise", states: ["SUBMETIDO", "EM_TRIAGEM"], color: "#3469ab" },
  { label: "Pendências", states: ["AGUARDANDO_CLIENTE", "AGUARDANDO_PROCURACAO"], color: "#a77318" },
  { label: "Aprovados", states: ["ACEITO"], color: "#397d78" },
  { label: "Em andamento", states: ["EM_PREPARACAO", "EM_ACOMPANHAMENTO"], color: "#5360a9" },
  { label: "Concluídos", states: ["ENCERRADO"], color: "#2a7b50" },
  { label: "Não aceitos", states: ["RECUSADO"], color: "#a34e56" },
];
export default function CaseStatusChart({ states }: { states: StateCount[] }) {
  const rows = groups.map(group => ({ ...group, count: states.filter(state => group.states.includes(state.id)).reduce((sum, state) => sum + state.count, 0) }));
  const maximum = Math.max(1, ...rows.map(row => row.count));
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return <section className="dashboard-card case-status-chart" aria-labelledby="case-chart-title">
    <h3 id="case-chart-title">Suas solicitações por situação</h3>
    <p>{total ? `${total} ${total === 1 ? "solicitação" : "solicitações"} no seu painel. Consulte os detalhes de cada caso na lista abaixo.` : "Você ainda não tem solicitações. Use Cadastrar ocorrência para começar."}</p>
    <ul>{rows.map(row => <li key={row.label}><span>{row.label}</span><div className="case-chart-track" aria-hidden="true"><div style={{ width: `${row.count / maximum * 100}%`, backgroundColor: row.color }} /></div><strong aria-label={`${row.count} ${row.label.toLowerCase()}`}>{row.count}</strong></li>)}</ul>
    <small>Após a aprovação, a associação prepara a procuração específica do caso para sua assinatura.</small>
  </section>;
}
