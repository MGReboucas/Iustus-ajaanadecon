"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api/client";
type RequestRow = { id: string; ownerEmail: string; kind: string; description: string; status: string; response: string; createdAt: string };
const kinds: Record<string, string> = { ACCESS: "Acesso aos dados", CORRECTION: "Correção", DELETION: "Exclusão", OTHER: "Outra solicitação" };
export default function AccountManagement({ admin }: { admin: boolean }) {
  const [requests, setRequests] = useState<RequestRow[]>([]);
  const [requestCursor, setRequestCursor] = useState<string | null>(null);
  const [kind, setKind] = useState("ACCESS");
  const [description, setDescription] = useState("");
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function loadRequests(cursor?: string) {
    const data = await api<{ results: RequestRow[]; nextCursor: string | null }>("privacy/requests" + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""));
    setRequests(old => cursor ? [...old, ...data.results] : data.results); setRequestCursor(data.nextCursor);
  }
  useEffect(() => { loadRequests().catch(e => setError(e.message)); }, [admin]);
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível concluir."); } finally { setBusy(false); }
  }
  function send(event: FormEvent) { event.preventDefault(); void run(async () => {
    await api("privacy/requests", { kind, description }); setDescription(""); await loadRequests(); setMessage("Solicitação registrada para análise.");
  }); }
  return <div className="dashboard-grid account-management">
    <section className="dashboard-card"><h2>Privacidade e dados pessoais</h2><p>Registre pedidos de acesso, correção ou exclusão. O escritório analisará o pedido e responderá aqui. O envio não apaga dados automaticamente.</p>
      <form onSubmit={send}><label>Tipo de solicitação<select value={kind} onChange={e => setKind(e.target.value)}>{Object.entries(kinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>Descreva sua solicitação<textarea required minLength={10} maxLength={4000} value={description} onChange={e => setDescription(e.target.value)} /></label><button disabled={busy}>Registrar solicitação</button></form>
      <button disabled={busy} onClick={() => run(() => loadRequests())}>Atualizar solicitações</button>
      <ul>{requests.map(item => <li key={item.id}><h3>{kinds[item.kind]} · {item.status === "OPEN" ? "Em análise" : "Respondida"}</h3>{admin && <p>{item.ownerEmail}</p>}<p>{item.description}</p>{item.response && <p>Resposta: {item.response}</p>}
      {admin && item.status === "OPEN" && <form onSubmit={event => { event.preventDefault(); void run(async () => { await api(`privacy/requests/${item.id}/resolve`, { response: responses[item.id] }); await loadRequests(); setMessage("Resposta registrada."); }); }}><label>Resposta à solicitação<textarea required minLength={10} maxLength={4000} value={responses[item.id] || ""} onChange={e => setResponses(old => ({ ...old, [item.id]: e.target.value }))} /></label><button disabled={busy}>Registrar resposta</button></form>}</li>)}</ul>
      {requestCursor && <button disabled={busy} onClick={() => run(() => loadRequests(requestCursor))}>Mais solicitações</button>}
    </section>{message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
  </div>;
}
