"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import "./admin-directory.css";
import AdminPersonDetails from "./AdminPersonDetails";

type Person = { id: string; name: string; email: string; role: string; active: boolean; activated: boolean; version: number };
type Directory = { results: Person[]; nextCursor: string | null; total: number; summary: { total: number; lawyers: number; clients: number; pending: number; revoked: number } };
const roles: Record<string, string> = { ADMIN: "Administrador", LAWYER: "Advogado", CLIENT: "Cliente" };

export default function AdminDirectory() {
  const [detailsId, setDetailsId] = useState<string>();
  const [data, setData] = useState<Directory>();
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState<string>();
  const [history, setHistory] = useState<(string | undefined)[]>([]);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<Person>();
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState("");
  const [email, setEmail] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    let current = true;
    setLoading(true); setError("");
    const params = new URLSearchParams({ role, status, search: query });
    if (cursor) params.set("cursor", cursor);
    api<Directory>(`admin/users?${params}`).then(result => { if (current) setData(result); })
      .catch(e => { if (current) { setData(undefined); setError(e.message); } })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [role, status, query, cursor, revision]);
  useEffect(() => { if (selected) dialog.current?.showModal(); }, [selected]);
  function resetPage() { setCursor(undefined); setHistory([]); }
  function filter(nextRole: string, nextStatus: string) { setRole(nextRole); setStatus(nextStatus); resetPage(); }
  function close() { dialog.current?.close(); setSelected(undefined); }
  async function changeAccess(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    setBusy(true); setActionError(""); setMessage("");
    try {
      await api(`admin/users/${selected.id}/access`, { active: !selected.active, version: selected.version, reason });
      setMessage(`${selected.active ? "Acesso revogado" : "Acesso aprovado"}: ${selected.email}.`);
      close(); setRevision(value => value + 1);
    } catch (e) { setActionError(e instanceof Error ? e.message : "Não foi possível alterar o acesso."); }
    finally { setBusy(false); }
  }
  async function invite(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const result = await api<{ message: string }>("admin/invitations", { email }); setMessage(result.message); setEmail(""); resetPage(); setRevision(value => value + 1); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível enviar a ativação."); }
    finally { setBusy(false); }
  }
  return <section className="admin-directory" aria-labelledby="directory-title">
    <div className="overview-heading"><div><p className="dashboard-eyebrow">ADMINISTRAÇÃO</p><h2 id="directory-title">Pessoas e acessos</h2><p>Gerencie sua equipe e os clientes em um só lugar.</p></div><button disabled={loading || busy} onClick={() => setRevision(value => value + 1)}>Atualizar usuários</button></div>
    <div className="admin-metrics">
      {([ ["Advogados ativos", "lawyers", "LAWYER", "active"], ["Clientes ativos", "clients", "CLIENT", "active"], ["Aguardando ativação", "pending", "", "pending"], ["Acessos revogados", "revoked", "", "revoked"] ] as const).map(([label, key, r, s]) => <button key={key} disabled={busy} aria-pressed={role === r && status === s} onClick={() => filter(r, s)}><span>{label}</span><strong>{data?.summary?.[key] ?? "—"}</strong><small>Ver lista →</small></button>)}
    </div>
    <p className="dashboard-note">Ativos = acesso liberado e e-mail confirmado. Esses números não indicam associação paga ou vigência financeira.</p>
    {message && <p role="status" aria-label="Resultado da gestão de usuários" className="admin-success">{message}</p>}
    {error && <p role="alert" className="dashboard-error">{error}</p>}
    <section className="dashboard-card admin-people"><div className="overview-heading"><h3>Gestão de usuários</h3><span>{data && !loading ? `${data.total} resultado(s)` : "Carregando…"}</span></div>
      <form className="admin-filters" onSubmit={e => { e.preventDefault(); resetPage(); setQuery(search.trim()); }}>
        <label>Buscar nome ou e-mail<input type="search" maxLength={150} value={search} onChange={e => setSearch(e.target.value)} placeholder="Digite um nome ou e-mail" /></label>
        <label>Perfil<select value={role} onChange={e => filter(e.target.value, status)}><option value="">Todos os perfis</option><option value="LAWYER">Advogados</option><option value="CLIENT">Clientes</option><option value="ADMIN">Administradores</option></select></label>
        <label>Situação do acesso<select value={status} onChange={e => filter(role, e.target.value)}><option value="">Todas as situações</option><option value="active">Ativo</option><option value="pending">Aguardando ativação</option><option value="revoked">Revogado</option></select></label>
        <button disabled={busy}>Buscar</button>
      </form>
      {(role || status || query) && <button className="admin-secondary" onClick={() => { filter("", ""); setSearch(""); setQuery(""); }}>Limpar filtros</button>}
      {loading ? <p role="status">Atualizando a lista…</p> : data && data.results.length === 0 ? <div className="case-empty-state"><h3>Nenhuma pessoa encontrada</h3><p>Tente outro nome, e-mail ou limpe os filtros.</p></div> : data && <div className="admin-table-wrap"><table><caption className="admin-sr-only">Usuários e permissões de acesso</caption><thead><tr><th scope="col">Pessoa</th><th scope="col">Perfil</th><th scope="col">Situação</th><th scope="col">Ações</th></tr></thead><tbody>{data.results.map(person => <tr key={person.id}><td><strong>{person.name || "Cadastro pendente"}</strong><span>{person.email}</span></td><td data-label="Perfil">{roles[person.role] || person.role}</td><td data-label="Situação"><span className={`admin-status ${!person.active ? "revoked" : person.activated ? "active" : "pending"}`}>{!person.active ? "Acesso revogado" : person.activated ? "Ativo" : "Aguardando ativação"}</span></td><td data-label="Ações"><button className="admin-secondary" disabled={busy} onClick={() => setDetailsId(person.id)}>Detalhes</button>{person.role === "ADMIN" ? <span className="dashboard-note">Gestão operacional</span> : <button className={person.active ? "admin-revoke" : "admin-approve"} disabled={busy} onClick={() => { setSelected(person); setReason(""); setActionError(""); }}>{person.active ? "Revogar acesso" : "Aprovar acesso"}</button>}</td></tr>)}</tbody></table></div>}
      <div className="admin-pagination"><span>Página {history.length + 1}</span><button className="admin-secondary" disabled={!history.length || loading || busy} onClick={() => { setCursor(history[history.length - 1]); setHistory(old => old.slice(0, -1)); }}>Anterior</button><button className="admin-secondary" disabled={!data?.nextCursor || loading || busy} onClick={() => { setHistory(old => [...old, cursor]); setCursor(data!.nextCursor!); }}>Próxima</button></div>
    </section>
    <section className="dashboard-card admin-invite"><div><p className="dashboard-eyebrow">AMPLIE SUA EQUIPE</p><h3>Aprovar profissional</h3><p>Cadastre o e-mail do advogado para enviar o link de ativação. Para reenviar uma ativação pendente, use o mesmo e-mail.</p></div><form onSubmit={invite}><label>E-mail do profissional<input type="email" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} placeholder="advogado@exemplo.com" /></label><button disabled={busy}>Aprovar e enviar ativação</button></form></section>
    {detailsId && <AdminPersonDetails key={detailsId} id={detailsId} onClose={() => setDetailsId(undefined)} />}
    <dialog className="admin-access-dialog" ref={dialog} onCancel={event => { if (busy) event.preventDefault(); }} onClose={() => setSelected(undefined)} aria-labelledby="access-dialog-title">
      {selected && <form onSubmit={changeAccess}><p className="dashboard-eyebrow">CONFIRMAR ALTERAÇÃO</p><h2 id="access-dialog-title">{selected.active ? "Revogar acesso" : "Aprovar acesso"}</h2><p><strong>{selected.name || selected.email}</strong><br />{selected.email}</p><p>{selected.active ? "Esta pessoa perderá o acesso ao sistema. As sessões e os links de ativação anteriores serão invalidados. Os registros serão preservados." : "O acesso será liberado. Isso não concede associação paga. Se a ativação estiver pendente, será necessário um novo link de ativação."}</p><label>Motivo da alteração<textarea autoFocus required minLength={10} maxLength={1000} value={reason} onChange={e => setReason(e.target.value)} /></label>{actionError && <p role="alert" className="dashboard-error">{actionError}</p>}<div className="case-actions"><button disabled={busy || reason.trim().length < 10}>Confirmar alteração de acesso</button><button type="button" className="admin-secondary" disabled={busy} onClick={close}>Cancelar</button></div></form>}
    </dialog>
  </section>;
}
