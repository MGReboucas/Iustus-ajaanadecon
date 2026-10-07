"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, Profile } from "@/lib/api/client";

import type { Message, Page as ApiPage } from "../../../contracts/api";
type Page = ApiPage<Message>;

export default function CaseMessages({ caseId, user, available, onChange }: { caseId: string; user: Profile; available: boolean; onChange: () => void }) {
  const [page, setPage] = useState<Page>({ results: [], nextCursor: null });
  const [text, setText] = useState("");
  const [internal, setInternal] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loaded, setLoaded] = useState(false);
  const alive = useRef(true);
  const retry = useRef<{ text: string; internal: boolean; id: string } | null>(null);

  function fail(reason: unknown) {
    if (!alive.current) return;
    if (reason instanceof ApiError && reason.code === "AUTH_REQUIRED") window.location.replace("/acessar");
    if (reason instanceof ApiError && reason.code === "NOT_FOUND") { setPage({ results: [], nextCursor: null }); setLoaded(false); }
    setError(reason instanceof Error ? reason.message : "Não foi possível carregar a conversa.");
  }
  async function load(cursor?: string) {
    const result = await api<Page>(`cases/${caseId}/messages${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`);
    if (alive.current) { setPage(old => ({ results: cursor ? [...old.results, ...result.results] : result.results, nextCursor: result.nextCursor })); setLoaded(true); }
  }
  useEffect(() => {
    alive.current = true;
    void load().catch(fail).finally(() => { if (alive.current) setBusy(false); });
    return () => { alive.current = false; };
  }, [caseId]);
  async function refresh(cursor?: string) {
    setBusy(true); setError(""); setNotice("");
    try { await load(cursor); onChange(); } catch (reason) { fail(reason); }
    finally { if (alive.current) setBusy(false); }
  }
  async function send(event: FormEvent) {
    event.preventDefault();
    const content = text.trim();
    if (!content || busy) return;
    if (retry.current?.text !== content || retry.current?.internal !== internal) retry.current = { text: content, internal, id: crypto.randomUUID() };
    setBusy(true); setError(""); setNotice("");
    try {
      await api(`cases/${caseId}/messages`, { text: content, visibility: internal ? "INTERNAL" : "PUBLIC", clientMessageId: retry.current.id });
      if (!alive.current) return;
      setText(""); retry.current = null;
      setNotice(internal ? "Nota interna registrada." : "Mensagem enviada.");
      onChange();
      await load();
    } catch (reason) { fail(reason); }
    finally { if (alive.current) setBusy(false); }
  }
  return <section className="case-messages" aria-labelledby="messages-title">
    <div className="cases-heading"><div><h4 id="messages-title">Conversa do caso</h4><p>Troque mensagens com {user.role === "CLIENT" ? "o advogado responsável" : "o cliente"}. As respostas ficam registradas aqui.</p></div><button type="button" disabled={busy} onClick={() => void refresh()}>Atualizar conversa</button></div>
    {error && <p role="alert" className="dashboard-error">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {busy && <p aria-live="polite">Carregando conversa…</p>}
    {loaded && !busy && page.results.length === 0 && <p>A conversa ainda não tem mensagens.</p>}
    {available ? <form onSubmit={send}><fieldset disabled={busy}>
      {user.role === "LAWYER" && <label className="case-check"><input type="checkbox" checked={internal} onChange={e => setInternal(e.target.checked)} />Registrar como nota interna (não visível ao cliente)</label>}
      <label>{internal ? "Nota interna" : "Sua mensagem"}<textarea required maxLength={10000} rows={4} value={text} onChange={e => setText(e.target.value)} /></label>
      <p className="message-audience">{internal ? "Visível somente ao advogado responsável, inclusive após transferência do caso." : "Visível ao cliente e ao advogado responsável."}</p>
      <button disabled={!text.trim()}>{internal ? "Salvar nota interna" : "Enviar mensagem"}</button>
    </fieldset></form> : <p>A conversa fica disponível após a atribuição de um advogado, enquanto o caso está em atendimento.</p>}
    <ol className="message-list" aria-label="Mensagens mais recentes primeiro">{page.results.map(item => <li key={item.id} className={item.visibility === "INTERNAL" ? "message-internal" : ""}>
      <div><strong>{item.authorId === user.id ? "Você" : item.authorName || "Responsável pelo caso"}</strong>{item.visibility === "INTERNAL" && <span className="case-badge">Nota interna · restrita</span>}<time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleString("pt-BR")}</time></div>
      <p className="case-narrative">{item.text}</p>
    </li>)}</ol>
    {page.nextCursor && <button disabled={busy} onClick={() => void refresh(page.nextCursor!)}>Mensagens anteriores</button>}
  </section>;
}
