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

export default function CaseStatusChart({ states, showCases }: { states: StateCount[]; showCases: () => void }) {
  const rows = groups.map(group => ({ ...group, count: states.filter(state => group.states.includes(state.id)).reduce((sum, state) => sum + state.count, 0) }));
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  let offset = 0;
  const slices = rows.filter(row => row.count > 0).map(row => {
    const start = offset;
    offset += row.count / total * 100;
    return row.color + " " + start + "% " + offset + "%";
  });
  return <section className="dashboard-card case-summary" aria-labelledby="case-chart-title">
    <div className="case-summary-heading"><h3 id="case-chart-title">Seus casos</h3><button onClick={showCases}>Ver casos <span aria-hidden="true">→</span></button></div>
    <div className="case-summary-body">
      <div className="case-summary-pie" role="img" aria-label={total ? "Distribuição dos casos por situação. Quantidades na legenda." : "Nenhum caso cadastrado"} style={{ background: total ? "conic-gradient(" + slices.join(", ") + ")" : "#28364b" }} />
      <div className="case-summary-details">
        <p className="case-summary-total"><strong>{total}</strong> {total === 1 ? "caso no total" : "casos no total"}</p>
        {total > 0 ? <ul>{rows.map(row => <li key={row.label}><span className="case-summary-dot" style={{ backgroundColor: row.color }} aria-hidden="true" /><span>{row.label}</span><strong>{row.count}</strong></li>)}</ul> : <p className="case-summary-empty">Você ainda não tem casos cadastrados.</p>}
      </div>
    </div>
  </section>;
}
