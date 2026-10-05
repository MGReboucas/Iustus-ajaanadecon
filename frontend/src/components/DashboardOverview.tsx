"use client";

import { useEffect, useState } from "react";
import { api, ApiError, Profile } from "@/lib/api/client";
import CaseStatusChart from "./CaseStatusChart";

type CaseLink = { id: string; reference: string; title?: string; stateLabel: string };
type Overview = { totalCases: number; attentionCount: number; unreadCount: number; states: { id: string; label: string; count: number }[]; attentionCases: CaseLink[]; recentActivity: { id: string; caseId: string; reference: string; title: string; action: string; stateLabel: string; createdAt: string }[]; submission: { message: string; expiresAt?: string; canSubmit: boolean } | null };
type Notice = { id: string; caseId: string; reference: string; title: string; createdAt: string; readAt: string | null };
type Notices = { results: Notice[]; nextCursor: string | null };
const actions: Record<string, string> = { MANDATE_GENERATED: "Procuração gerada", LEGAL_START: "Procuração solicitada", LEGAL_SIGN: "Procuração devolvida", LEGAL_VERIFY: "Procuração conferida", LEGAL_RETURN_MANDATE: "Correção da procuração solicitada", LEGAL_DRAFT: "Minuta interna atualizada", LEGAL_PUBLISH: "Peça publicada", LEGAL_FILE: "Protocolo registrado", LEGAL_UPDATE: "Movimentação publicada", LEGAL_TASK: "Compromisso agendado", LEGAL_RESCHEDULE: "Compromisso remarcado", LEGAL_COMPLETE: "Compromisso concluído", LEGAL_CLOSE: "Atendimento encerrado", SUBMITTED: "Caso enviado", TRIAGE_STARTED: "Triagem iniciada", TRIAGE_DECISION: "Triagem concluída", INFORMATION_REQUESTED: "Complemento solicitado", INFORMATION_RESPONDED: "Complemento recebido", INFORMATION_RESOLVED: "Complemento conferido", DOCUMENT_UPLOADED: "Documento enviado" };

export default function DashboardOverview({ user, revision, openCase }: { user: Profile; revision: number; openCase: (id: string) => void }) {
  const [overview, setOverview] = useState<Overview>();
  const [notices, setNotices] = useState<Notices>({ results: [], nextCursor: null });
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const admin = user.role === "ADMIN";
  useEffect(() => {
    const timer = setInterval(() => { if (!document.hidden) setRefresh(value => value + 1); }, 30000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    let current = true;
    setBusy(true); setError("");
    Promise.all([api<Overview>("dashboard/overview"), api<Notices>(`notifications?unread=${unreadOnly}`)])
      .then(([summary, notifications]) => { if (current) { setOverview(summary); setNotices(notifications); } })
      .catch(reason => { if (current) { setOverview(undefined); setNotices({ results: [], nextCursor: null }); setError(reason.message); if (reason instanceof ApiError && reason.code === "AUTH_REQUIRED") window.location.replace("/acessar"); } })
      .finally(() => { if (current) setBusy(false); });
    return () => { current = false; };
  }, [user.id, revision, refresh, unreadOnly]);
  async function markRead(item: Notice) {
    setBusy(true); setError("");
    try { await api(`notifications/${item.id}/read`, {}); setRefresh(value => value + 1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível marcar o aviso."); setBusy(false); }
  }
  async function more() {
    if (!notices.nextCursor) return;
    setBusy(true); setError("");
    try {
      const result = await api<Notices>(`notifications?unread=${unreadOnly}&cursor=${encodeURIComponent(notices.nextCursor)}`);
      setNotices(old => ({ results: [...old.results, ...result.results], nextCursor: result.nextCursor }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar avisos."); }
    finally { setBusy(false); }
  }
  return <section className="dashboard-overview" aria-label="Resumo do atendimento">
    <div className="overview-heading"><h2>Visão geral</h2><button disabled={busy} onClick={() => setRefresh(value => value + 1)}>Atualizar painel</button></div>
    {error && <p role="alert" className="dashboard-error">{error}</p>}
    {busy && <p aria-live="polite">Atualizando resumo…</p>}
    {overview && <>
      <div className="dashboard-metrics">
        <article><span>{admin ? "Casos recebidos" : "Seus casos"}</span><strong>{overview.totalCases}</strong><small>{admin ? "Fila do escritório" : "No seu acompanhamento"}</small></article>
        <article><span>{admin ? "Sem responsável" : "Precisam de você"}</span><strong>{overview.attentionCount}</strong><small>{admin ? "Aguardando distribuição" : user.role === "CLIENT" ? "Rascunhos, documentos e complementos" : "Triagens, preparação e compromissos vencidos"}</small></article>
        {!admin && <article><span>Avisos não lidos</span><strong>{overview.unreadCount}</strong><small>Novidades dos seus casos</small></article>}
      </div>
      {user.role === "CLIENT" ? <CaseStatusChart states={overview.states} /> : <div className="overview-states" aria-label="Casos por estado">{overview.states.filter(state => state.count > 0).map(state => <span key={state.id}>{state.label} <strong>{state.count}</strong></span>)}</div>}
      <div className="dashboard-grid overview-panels">
        <section className="dashboard-card"><h3>{admin ? "Para distribuir" : "Próximos passos"}</h3>
          {overview.attentionCases.length === 0 ? <p>Nenhuma ação pendente neste momento.</p> : <><p>{overview.attentionCount > 5 ? "Mostrando os 5 casos que aguardam há mais tempo." : "Abra um caso para continuar o atendimento."}</p><ul className="overview-list">{overview.attentionCases.map(item => <li key={item.id}><button onClick={() => openCase(item.id)}><strong>{item.title || `Caso ${item.reference}`}</strong><small>{item.stateLabel} · {item.reference}</small></button></li>)}</ul></>}
        </section>
        {!admin && <section className="dashboard-card"><h3>Últimas atualizações</h3>{overview.recentActivity.length === 0 ? <p>As atualizações aparecerão aqui depois do envio de um caso.</p> : <ul className="overview-list">{overview.recentActivity.map(item => <li key={item.id}><button onClick={() => openCase(item.caseId)}><strong>{actions[item.action] || "Caso atualizado"}</strong><small>{item.title || item.reference} · {item.stateLabel}</small><time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleString("pt-BR")}</time></button></li>)}</ul>}</section>}
      </div>
      <section className="dashboard-card dashboard-notices"><div className="overview-heading"><div><h3>Central de avisos</h3><p>Mensagens e novidades do seu atendimento.</p></div><label className="notice-filter"><input type="checkbox" disabled={busy} checked={unreadOnly} onChange={e => setUnreadOnly(e.target.checked)} />Somente não lidos</label></div>
        {notices.results.length === 0 && <p>{unreadOnly ? "Nenhum aviso não lido." : "Você ainda não tem avisos."}</p>}
        <ul className="notification-list">{notices.results.map(item => <li key={item.id} className={item.readAt ? "" : "notification-unread"}><div><span className="notice-label">{item.readAt ? "Lido" : "Novo"} · Caso {item.reference}</span><p>{item.title}</p><time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleString("pt-BR")}</time></div><div className="notification-actions"><button onClick={() => openCase(item.caseId)}>Abrir caso</button>{!item.readAt && <button disabled={busy} onClick={() => void markRead(item)}>Marcar como lido</button>}</div></li>)}</ul>
        {notices.nextCursor && <button disabled={busy} onClick={() => void more()}>Mais avisos</button>}
      </section>
      {overview.submission && <p className="dashboard-note">{overview.submission.message}{overview.submission.expiresAt && <> Vigência até {new Date(overview.submission.expiresAt).toLocaleDateString("pt-BR")}.</>}{!overview.submission.canSubmit && <> <a href="/checkout">Associar-me ou renovar</a></>}</p>}
    </>}
  </section>;
}
