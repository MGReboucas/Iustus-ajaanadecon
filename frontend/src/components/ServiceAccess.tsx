"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api/client";
type Grant = {email: string; enabled: boolean; expiresAt: string; reason: string};
export default function ServiceAccess() {
  const [email, setEmail] = useState("");
  const [expires, setExpires] = useState("");
  const [reason, setReason] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [rows, setRows] = useState<Grant[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  async function load(next?: string) {
    const result = await api<{results: Grant[]; nextCursor: string | null}>(`admin/service-access${next ? `?cursor=${encodeURIComponent(next)}` : ""}`);
    setRows(old => next ? [...old, ...result.results] : result.results); setCursor(result.nextCursor);
  }
  useEffect(() => {load().catch(e => setError(e.message));}, []);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const result = await api<{message: string}>("admin/service-access", {email, enabled, reason, ...(enabled ? {expiresAt: new Date(expires).toISOString()} : {})});
      setMessage(result.message); await load();
    } catch(e) {setError(e instanceof Error ? e.message : "Não foi possível atualizar.");}
    finally {setBusy(false);}
  }
  return <section className="dashboard-card"><h2>Liberação de atendimento</h2><p>Autorize clientes cadastrados e com e-mail confirmado a enviar casos. A validade controla novos envios; os casos em andamento continuam acessíveis.</p>
    <form onSubmit={save}><fieldset disabled={busy}><label>E-mail do cliente<input type="email" required value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label>Ação de atendimento<select value={enabled ? "grant" : "revoke"} onChange={e => setEnabled(e.target.value === "grant")}><option value="grant">Liberar atendimento</option><option value="revoke">Revogar novos envios</option></select></label>
    {enabled && <label>Validade da liberação<input type="datetime-local" required value={expires} onChange={e => setExpires(e.target.value)} /></label>}
    <label>Motivo da liberação<textarea required minLength={5} maxLength={240} value={reason} onChange={e => setReason(e.target.value)} /></label><button>Salvar liberação</button></fieldset></form>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <ul>{rows.map(row => <li key={row.email}><strong>{row.email}</strong> · {row.enabled && new Date(row.expiresAt) > new Date() ? "Liberado" : "Inativo"} · {new Date(row.expiresAt).toLocaleString("pt-BR")}<p>{row.reason}</p></li>)}</ul>
    {cursor && <button disabled={busy} onClick={async () => {setBusy(true); try {await load(cursor);} catch(e) {setError(e instanceof Error ? e.message : "Falha ao carregar.");} finally {setBusy(false);}}}>Mais liberações</button>}
  </section>;
}
