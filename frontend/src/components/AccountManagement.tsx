"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api/client";
type UserRow = { id: string; name: string; email: string; role: string; active: boolean; version: number };
type RequestRow = { id: string; ownerEmail: string; kind: string; description: string; status: string; response: string; createdAt: string };
const kinds: Record<string, string> = { ACCESS: "Acesso aos dados", CORRECTION: "Correção", DELETION: "Exclusão", OTHER: "Outra solicitação" };
export default function AccountManagement({ admin }: { admin: boolean }) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [requests, setRequests] = useState<RequestRow[]>([]);
  const [userCursor, setUserCursor] = useState<string | null>(null);
  const [requestCursor, setRequestCursor] = useState<string | null>(null);
  const [kind, setKind] = useState("ACCESS");
  const [description, setDescription] = useState("");
  const [reason, setReason] = useState("");
  const [selected, setSelected] = useState<UserRow>();
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function loadUsers(cursor?: string) {
    const data = await api<{ results: UserRow[]; nextCursor: string | null }>("admin/users" + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""));
    setUsers(old => cursor ? [...old, ...data.results] : data.results); setUserCursor(data.nextCursor);
  }
  async function loadRequests(cursor?: string) {
    const data = await api<{ results: RequestRow[]; nextCursor: string | null }>("privacy/requests" + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""));
    setRequests(old => cursor ? [...old, ...data.results] : data.results); setRequestCursor(data.nextCursor);
  }
  useEffect(() => { Promise.all([loadRequests(), ...(admin ? [loadUsers()] : [])]).catch(e => setError(e.message)); }, [admin]);
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível concluir."); } finally { setBusy(false); }
  }
  function send(event: FormEvent) { event.preventDefault(); void run(async () => {
    await api("privacy/requests", { kind, description }); setDescription(""); await loadRequests(); setMessage("Solicitação registrada para análise.");
  }); }
  function access(event: FormEvent) { event.preventDefault(); if (!selected) return; void run(async () => {
    await api(`admin/users/${selected.id}/access`, { active: !selected.active, version: selected.version, reason });
    setSelected(undefined); setReason(""); await loadUsers(); setMessage("Acesso atualizado. As sessões anteriores foram invalidadas.");
  }); }
  return <div className="dashboard-grid account-management">
    {admin && <section className="dashboard-card"><h2>Gestão de usuários</h2><button disabled={busy} onClick={() => run(() => loadUsers())}>Atualizar usuários</button>
      <ul>{users.map(user => <li key={user.id}><strong>{user.name || user.email}</strong><p>{user.email} · {user.role} · {user.active ? "Ativo" : "Suspenso"}</p>{user.role !== "ADMIN" && <button disabled={busy} onClick={() => { setSelected(user); setReason(""); }}>{user.active ? "Suspender" : "Reativar"} acesso</button>}</li>)}</ul>
      {userCursor && <button disabled={busy} onClick={() => run(() => loadUsers(userCursor))}>Mais usuários</button>}
      {selected && <form onSubmit={access}><h3>{selected.active ? "Suspender" : "Reativar"}: {selected.email}</h3><label>Motivo da alteração<textarea required minLength={10} maxLength={1000} value={reason} onChange={e => setReason(e.target.value)} /></label><button disabled={busy}>Confirmar alteração de acesso</button><button type="button" disabled={busy} onClick={() => setSelected(undefined)}>Cancelar</button></form>}
    </section>}
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
