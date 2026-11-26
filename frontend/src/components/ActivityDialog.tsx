"use client";
import { useState, type RefObject } from "react";
import { api } from "@/lib/api/client";
import type { Page, RecentActivity } from "../../../contracts/api";
import eventLabels from "../../../contracts/events.json";

const actions: Record<string, string> = eventLabels;
export default function ActivityDialog({ dialogRef, openCase }: { dialogRef: RefObject<HTMLDialogElement | null>; openCase: (id: string) => void }) {
  const [page, setPage] = useState<Page<RecentActivity>>({ results: [], nextCursor: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(cursor?: string) {
    setBusy(true); setError("");
    try {
      const result = await api<Page<RecentActivity>>(`dashboard/overview?activity=all${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`);
      setPage(old => cursor ? { ...result, results: [...old.results, ...result.results.filter(item => !old.results.some(existing => existing.id === item.id))] } : result);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar as atualizações."); }
    finally { setBusy(false); }
  }
  return <dialog ref={dialogRef} className="overview-activity-dialog" aria-labelledby="activity-title" onToggle={event => { if (event.newState === "open") void load(); }}>
    <div className="overview-heading"><h2 id="activity-title">Todas as atualizações</h2><button autoFocus onClick={() => dialogRef.current?.close()}>Fechar</button></div>
    <ul className="overview-list">{page.results.map(item => <li key={item.id}><button onClick={() => { dialogRef.current?.close(); openCase(item.caseId); }}><strong>{actions[item.action] || "Caso atualizado"}</strong><small>{item.title || item.reference} · {item.stateLabel}</small><time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleString("pt-BR")}</time></button></li>)}</ul>
    {busy && <p role="status">Carregando atualizações…</p>}
    {error && <div role="alert"><p className="dashboard-error">{error}</p><button disabled={busy} onClick={() => void load(page.nextCursor || undefined)}>Tentar novamente</button></div>}
    {!busy && !error && !page.results.length && <p>Nenhuma atualização disponível.</p>}
    {page.nextCursor && !error && <button disabled={busy} onClick={() => void load(page.nextCursor!)}>Carregar mais</button>}
  </dialog>;
}
