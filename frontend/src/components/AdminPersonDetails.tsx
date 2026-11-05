"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";

type Event = { id: string; createdAt: string; active: boolean; reason: string; actor: string };
type Details = { user: { name: string; email: string; active: boolean; activated: boolean }; joinedAt: string; membership: null | { status: string; environment: string; startsAt: string | null; expiresAt: string | null }; results: Event[]; nextCursor: string | null };
const labels: Record<string, string> = { ACTIVE: "Associação vigente", EXPIRED: "Associação vencida", REVOKED: "Associação revogada ou pagamento sem validade", UPCOMING: "Vigência futura", NONE: "Sem associação registrada" };
const date = (value: string) => new Date(value).toLocaleString("pt-BR");

export default function AdminPersonDetails({ id, onClose }: { id: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [data, setData] = useState<Details>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => { dialog.current?.showModal(); }, []);
  useEffect(() => {
    let current = true;
    setBusy(true); setError(""); setData(undefined);
    api<Details>(`admin/users/${id}/details`).then(value => { if (current) setData(value); })
      .catch(e => { if (current) setError(e.message); }).finally(() => { if (current) setBusy(false); });
    return () => { current = false; };
  }, [id, revision]);
  async function more() {
    if (!data?.nextCursor) return;
    setBusy(true); setError("");
    try { const value = await api<Details>(`admin/users/${id}/details?cursor=${encodeURIComponent(data.nextCursor)}`); setData(old => old ? { ...old, results: [...old.results, ...value.results], nextCursor: value.nextCursor } : value); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível carregar o histórico."); }
    finally { setBusy(false); }
  }
  return <dialog ref={dialog} className="admin-access-dialog admin-details-dialog" aria-labelledby="person-details-title" onClose={onClose}>
    <div className="overview-heading"><h2 id="person-details-title">Detalhes da pessoa</h2><button className="admin-secondary" onClick={() => dialog.current?.close()} autoFocus>Fechar</button></div>
    {error && <p className="dashboard-error" role="alert">{error} <button disabled={busy} onClick={() => setRevision(value => value + 1)}>Tentar novamente</button></p>}
    {busy && <p role="status">Carregando informações…</p>}
    {data && <><h3>{data.user.name || "Cadastro pendente"}</h3><p>{data.user.email}</p><dl className="admin-person-facts"><div><dt>Acesso ao sistema</dt><dd>{!data.user.active ? "Revogado" : data.user.activated ? "Ativo" : "Aguardando ativação"}</dd></div><div><dt>Cadastro em</dt><dd>{date(data.joinedAt)}</dd></div></dl>
      {data.membership && <section className="admin-membership"><h3>Associação do cliente</h3><p><strong>{labels[data.membership.status] || "Situação indisponível"}</strong></p><p className="dashboard-note">Ambiente: {data.membership.environment === "production" ? "Produção" : "Teste"}. A associação e a permissão de acesso são controles independentes.</p><dl className="admin-person-facts"><div><dt>Início da vigência</dt><dd>{data.membership.startsAt ? date(data.membership.startsAt) : "Não registrado"}</dd></div><div><dt>Fim da vigência</dt><dd>{data.membership.expiresAt ? date(data.membership.expiresAt) : "Não registrado"}</dd></div></dl></section>}
      <section className="admin-access-history"><h3>Histórico de acessos</h3><p className="dashboard-note">Aprovações e revogações registradas pelo administrador.</p>{data.results.length === 0 ? <p>Nenhuma alteração de acesso registrada.</p> : <ol>{data.results.map(event => <li key={event.id}><strong>{event.active ? "Acesso aprovado" : "Acesso revogado"}</strong><time dateTime={event.createdAt}>{date(event.createdAt)}</time><p>Por: {event.actor}</p><p className="admin-audit-reason">{event.reason || "Motivo não registrado"}</p></li>)}</ol>}{data.nextCursor && <button disabled={busy} onClick={more}>Mais registros</button>}</section>
    </>}
  </dialog>;
}
