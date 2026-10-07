"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, Profile } from "@/lib/api/client";

type Proposal = { id: string; number: number; scope: string; feeCents: number; expenses: string; paymentTerms: string; validUntil: string; status: "OPEN" | "ACCEPTED" | "DECLINED" | "SUPERSEDED"; decidedAt: string | null };
type Page = { results: Proposal[]; nextCursor: string | null };
type Props = { caseId: string; version: number; state: string; user: Profile; onChange: () => Promise<void> };
const labels = { OPEN: "Aguardando decisão", ACCEPTED: "Aceita", DECLINED: "Recusada", SUPERSEDED: "Substituída" };
const money = (cents: number) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function CaseProposals({ caseId, version, state, user, onChange }: Props) {
  const [page, setPage] = useState<Page>({ results: [], nextCursor: null });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [confirmed, setConfirmed] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const mounted = useRef(false);
  const pending = useRef(false);
  const generation = useRef(0);
  const closed = ["RASCUNHO", "RECUSADO", "ENCERRADO"].includes(state);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const current = ++generation.current;
    setLoading(true); setError(""); setConfirmed(null);
    api<Page>(`cases/${caseId}/proposals`).then(result => {
      if (mounted.current && generation.current === current) setPage(result);
    }).catch(e => {
      if (mounted.current && generation.current === current) { setError(e.message); setPage({ results: [], nextCursor: null }); }
    }).finally(() => { if (mounted.current && generation.current === current) setLoading(false); });
  }, [caseId, version, refresh]);

  async function mutate(path: string, body: object, form?: HTMLFormElement) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError(""); setMessage("");
    try {
      await api(path, body);
      if (!mounted.current) return;
      form?.reset(); setConfirmed(null); setMessage("Proposta registrada. Nenhuma cobrança foi realizada por esta ação.");
      setRefresh(n => n + 1);
      try { await onChange(); } catch { if (mounted.current) setError("A ação foi registrada, mas o caso não foi atualizado. Reabra o caso antes de outra alteração."); }
    } catch (e) { if (mounted.current) setError(e instanceof Error ? e.message : "Não foi possível registrar. Atualize as propostas para conferir o resultado antes de tentar novamente."); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  }
  function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const value = String(data.get("fee")).trim().replace(",", ".");
    if (!/^\d{1,9}(\.\d{1,2})?$/.test(value)) { setError("Informe os honorários em reais, sem separador de milhar, com até duas casas decimais."); return; }
    const [reais, centavos = ""] = value.split(".");
    const feeCents = Number(reais) * 100 + Number(centavos.padEnd(2, "0"));
    const date = new Date(String(data.get("validUntil")));
    if (!Number.isFinite(date.getTime()) || date.getTime() <= Date.now()) { setError("Informe uma validade futura."); return; }
    void mutate(`cases/${caseId}/proposals`, { version, scope: data.get("scope"), feeCents, expenses: data.get("expenses"), paymentTerms: data.get("paymentTerms"), validUntil: date.toISOString() }, form);
  }
  async function more() {
    if (!page.nextCursor || pending.current) return;
    const current = generation.current;
    pending.current = true; setBusy(true); setError("");
    try {
      const result = await api<Page>(`cases/${caseId}/proposals?cursor=${encodeURIComponent(page.nextCursor)}`);
      if (mounted.current && current === generation.current) setPage(previous => ({ results: [...previous.results, ...result.results.filter(row => !previous.results.some(old => old.id === row.id))], nextCursor: result.nextCursor }));
    } catch (e) { if (mounted.current) setError(e instanceof Error ? e.message : "Não foi possível carregar mais propostas."); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  }
  return <section className="legal-workflow" aria-label="Propostas de atendimento">
    <div className="cases-heading"><h4>Propostas de atendimento</h4><button type="button" disabled={busy || loading} onClick={() => setRefresh(n => n + 1)}>Atualizar propostas</button></div>
    <p>A assinatura dá acesso à plataforma. Honorários, custas, audiências e outras despesas são contratados separadamente por caso.</p>
    {error && <p role="alert" className="dashboard-error">{error}</p>}
    {message && <p role="status">{message}</p>}
    {loading ? <p role="status">Carregando propostas…</p> : <>
      {!page.results.length && !error && <p>Nenhuma proposta apresentada neste caso.</p>}
      {page.results.map(row => {
        const expired = Date.parse(row.validUntil) <= Date.now();
        return <article key={row.id} className="dashboard-card">
          <h5>Proposta {row.number} · {row.status === "OPEN" && expired ? "Expirada" : labels[row.status]}</h5>
          <p><strong>Honorários: {money(row.feeCents)}</strong></p>
          <p className="case-narrative"><strong>Escopo:</strong>{"\n"}{row.scope}</p>
          <p className="case-narrative"><strong>Despesas:</strong>{"\n"}{row.expenses}</p>
          <p className="case-narrative"><strong>Condições de pagamento:</strong>{"\n"}{row.paymentTerms}</p>
          <p>Válida até {new Date(row.validUntil).toLocaleString("pt-BR")}</p>
          {row.decidedAt && <p>Decisão registrada em {new Date(row.decidedAt).toLocaleString("pt-BR")}</p>}
          {user.role === "CLIENT" && !closed && row.status === "OPEN" && !expired && <fieldset disabled={busy}>
            <label><input type="checkbox" checked={confirmed === row.id} onChange={e => setConfirmed(e.target.checked ? row.id : null)} />Li o escopo, os honorários, as despesas e as condições desta proposta.</label>
            <div className="case-actions"><button type="button" disabled={confirmed !== row.id} onClick={() => void mutate(`cases/${caseId}/proposals/${row.id}/decision`, { version, accepted: true })}>Aceitar proposta {row.number}</button><button type="button" onClick={() => void mutate(`cases/${caseId}/proposals/${row.id}/decision`, { version, accepted: false })}>Recusar proposta {row.number}</button></div>
          </fieldset>}
        </article>;
      })}
      {page.nextCursor && <button type="button" disabled={busy} onClick={() => void more()}>Mais propostas</button>}
    </>}
    {user.role === "LAWYER" && !closed && <form onSubmit={publish}><fieldset disabled={busy || loading}>
      <legend>Apresentar nova proposta</legend>
      <p>Uma nova versão substitui a proposta ainda aberta. Propostas aceitas permanecem no histórico.</p>
      <label>Escopo do atendimento<textarea name="scope" required maxLength={50000} /></label>
      <label>Honorários em reais<input name="fee" inputMode="decimal" required placeholder="1500,00" maxLength={12} /></label>
      <label>Custas e outras despesas<textarea name="expenses" required maxLength={50000} /></label>
      <label>Condições de pagamento<textarea name="paymentTerms" required maxLength={50000} /></label>
      <label>Validade da proposta<input name="validUntil" type="datetime-local" required /></label>
      <button type="submit">Apresentar proposta ao cliente</button>
    </fieldset></form>}
  </section>;
}
