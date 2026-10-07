"use client";
import CaseProposals from "./CaseProposals";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, Profile } from "@/lib/api/client";
import { DocumentVersion, downloadDocument } from "@/lib/api/documents";
import CaseDocuments from "./CaseDocuments";
import CaseMessages from "./CaseMessages";
import LegalWorkflow from "./LegalWorkflow";
import CaseExport from "./CaseExport";
import "./cases.css";

type CaseItem = { id: string; reference: string; title?: string; description?: string; occurredOn?: string | null; category: string; categoryLabel: string; state: string; stateLabel: string; version: number; lawyerId: string | null; scopeAcknowledged?: boolean };
type Page<T> = { results: T[]; nextCursor: string | null };
type Catalog = { documentsAvailable: boolean; intakeRequired: boolean; categories: { id: string; label: string }[]; states: { id: string; label: string }[]; submission: { canSubmit: boolean; message: string } | null };
type Pending = { id: string; description: string; response: string; resolution: string; resolved: boolean; responded: boolean; attachments: DocumentVersion[] };
type Event = { id: string; action: string; state: string; reason: string; createdAt: string };
type Lawyer = { id: string; name: string; email: string };
const labels: Record<string, string> = { PROPOSAL_PUBLISHED: "Proposta apresentada", PROPOSAL_ACCEPTED: "Proposta aceita", PROPOSAL_DECLINED: "Proposta recusada", MANDATE_GENERATED: "Procuração gerada", LEGAL_START: "Procuração solicitada", LEGAL_SIGN: "Procuração devolvida", LEGAL_VERIFY: "Procuração conferida", LEGAL_RETURN_MANDATE: "Correção da procuração solicitada", LEGAL_DRAFT: "Minuta interna atualizada", LEGAL_PUBLISH: "Peça publicada", LEGAL_FILE: "Protocolo registrado", LEGAL_UPDATE: "Movimentação publicada", LEGAL_TASK: "Compromisso agendado", LEGAL_RESCHEDULE: "Compromisso remarcado", LEGAL_COMPLETE: "Compromisso concluído", LEGAL_CLOSE: "Atendimento encerrado", DRAFT_CREATED: "Rascunho criado", DRAFT_UPDATED: "Rascunho atualizado", SUBMITTED: "Caso enviado", ASSIGNED: "Responsável atribuído", TRIAGE_STARTED: "Triagem iniciada", TRIAGE_DECISION: "Decisão de triagem", INFORMATION_REQUESTED: "Complemento solicitado", INFORMATION_RESPONDED: "Complemento recebido", INFORMATION_RESOLVED: "Complemento conferido" };

export default function CasesWorkspace({ user, openCase, onChange }: { user: Profile; openCase?: { id: string; sequence: number }; onChange: () => void }) {
  const [catalog, setCatalog] = useState<Catalog>();
  const [rows, setRows] = useState<CaseItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<CaseItem>();
  const [requests, setRequests] = useState<Page<Pending>>({ results: [], nextCursor: null });
  const [events, setEvents] = useState<Page<Event>>({ results: [], nextCursor: null });
  const [documents, setDocuments] = useState<Page<DocumentVersion>>({ results: [], nextCursor: null });
  const [attachments, setAttachments] = useState<string[]>([]);
  const [lawyers, setLawyers] = useState<Page<Lawyer>>({ results: [], nextCursor: null });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [occurredOn, setOccurredOn] = useState("");
  const [category, setCategory] = useState("");
  const [ack, setAck] = useState(false);
  const [reason, setReason] = useState("");
  const [lawyer, setLawyer] = useState("");
  const [complement, setComplement] = useState("");
  const [checks, setChecks] = useState([false, false, false]);
  const submission = useRef<{ id: string; version: number; key: string } | null>(null);
  const admin = user.role === "ADMIN", client = user.role === "CLIENT";

  async function list(state = filter, next?: string) {
    const query = new URLSearchParams();
    if (state) query.set("state", state);
    if (next) query.set("cursor", next);
    const result = await api<Page<CaseItem>>(`cases?${query}`);
    setRows(old => next ? [...old, ...result.results] : result.results); setCursor(result.nextCursor);
  }
  async function load(item: CaseItem) {
    setReason(""); setComplement(""); setAttachments([]); setChecks([false, false, false]);
    if (admin) { setSelected(item); setLawyer(item.lawyerId || ""); return; }
    const [detail, pending, history, files] = await Promise.all([
      api<CaseItem>(`cases/${item.id}`), api<Page<Pending>>(`cases/${item.id}/requests`), api<Page<Event>>(`cases/${item.id}/timeline`),
      api<Page<DocumentVersion>>(`cases/${item.id}/documents`),
    ]);
    setSelected(detail); setTitle(detail.title || ""); setDescription(detail.description || ""); setOccurredOn(detail.occurredOn || "");
    setCategory(detail.category); setAck(!!detail.scopeAcknowledged); setRequests(pending); setEvents(history);
    setDocuments(files);
  }
  async function refreshDocuments() {
    if (!selected) return;
    const [files, detail, history] = await Promise.all([api<Page<DocumentVersion>>(`cases/${selected.id}/documents`), api<CaseItem>(`cases/${selected.id}`), api<Page<Event>>(`cases/${selected.id}/timeline`)]);
    setDocuments(files); setSelected(detail); setEvents(history); setAttachments([]);
  }
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); }
    catch (e) {
      if (e instanceof ApiError && e.code === "AUTH_REQUIRED") window.location.replace("/acessar");
      else {
        setError(e instanceof Error ? e.message : "Não foi possível concluir.");
        if (e instanceof ApiError && e.code === "NOT_FOUND") setSelected(undefined);
      }
    } finally { setBusy(false); }
  }
  useEffect(() => { void run(async () => {
    setCatalog(await api<Catalog>("cases/catalog")); await list("");
    if (admin) setLawyers(await api<Page<Lawyer>>("cases/lawyers"));
  }); }, [user.id]); // A identidade define o escopo; filtros são carregados explicitamente.
  useEffect(() => {
    if (!openCase) return;
    setSelected(undefined);
    void run(async () => {
      const item = await api<CaseItem>(`cases/${openCase.id}${admin ? "/summary" : ""}`);
      await load(item);
      document.getElementById("meus-casos")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [openCase]);

  async function change(route: string, body: object, method?: "PATCH", idempotencyKey?: string) {
    const result = await api<CaseItem>(route, body, { method, idempotencyKey });
    onChange();
    await list(); await load(result); setNotice("Alteração registrada.");
  }
  function save(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    void run(() => change(`cases/${selected.id}`, { version: selected.version, title, description, category, occurredOn: occurredOn || null, scopeAcknowledged: ack }, "PATCH"));
  }
  function submit() {
    if (!selected) return;
    if (submission.current?.id !== selected.id || submission.current?.version !== selected.version) submission.current = { id: selected.id, version: selected.version, key: crypto.randomUUID() };
    const key = submission.current.key;
    void run(() => change(`cases/${selected.id}/submit`, { version: selected.version }, undefined, key));
  }
  const dirty = selected && (occurredOn !== (selected.occurredOn || "") || title !== (selected.title || "") || description !== (selected.description || "") || category !== selected.category || ack !== !!selected.scopeAcknowledged);

  return <section id="meus-casos" className="cases-workspace" aria-labelledby="cases-title">
    <div className="cases-heading"><div><h2 id="cases-title">{admin ? "Distribuição de casos" : client ? "Meus casos" : "Casos atribuídos"}</h2><p>{admin ? "A fila mostra apenas referência, categoria, estado e responsável. Relatos ficam restritos ao cliente e ao advogado atribuído." : "Multas de trânsito e direito civil, exceto família e sucessões."}</p></div>
      {client && <button disabled={busy} onClick={() => void run(async () => { const item = await api<CaseItem>("cases", {}); onChange(); setFilter(""); await list(""); await load(item); })}>Cadastrar ocorrência</button>}
    </div>
    <p className="dashboard-note">Cada ocorrência é analisada individualmente. Após o aceite, a associação envia a procuração específica deste caso para sua assinatura.</p>
    {client && <p className="case-access">{catalog?.submission?.message}</p>}
    {error && <p role="alert" className="dashboard-error">{error} <button disabled={busy} onClick={() => void run(async () => { await list(); if (selected) await load(selected); })}>Atualizar dados</button></p>}
    {notice && <p role="status">{notice}</p>}
    <label className="case-filter">Filtrar por estado<select value={filter} disabled={busy} onChange={e => { const state = e.target.value; setFilter(state); setSelected(undefined); void run(() => list(state)); }}><option value="">Todos</option>{catalog?.states.filter(s => !admin || s.id !== "RASCUNHO").map(s => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
    {busy && <p aria-live="polite">Carregando…</p>}
    {!busy && rows.length === 0 && <p>Nenhum caso encontrado neste filtro.</p>}
    <div className="case-list">{rows.map(item => <button className="case-row" aria-pressed={selected?.id === item.id} key={item.id} disabled={busy} onClick={() => void run(() => load(item))}>
      <span><strong>{admin ? `Caso ${item.reference}` : item.title || "Rascunho sem título"}</strong><small>{item.categoryLabel || "Categoria não informada"} · {item.reference}</small></span><span className="case-badge">{item.stateLabel}{admin && !item.lawyerId ? " · Sem responsável" : ""}</span>
    </button>)}</div>
    {cursor && <button disabled={busy} onClick={() => void run(() => list(filter, cursor))}>Mais casos</button>}

    {selected && <article className="case-detail" aria-labelledby="case-detail-title">
      <div className="cases-heading"><h3 id="case-detail-title">Caso {selected.reference}</h3><span className="case-badge">{selected.stateLabel}</span></div>
      {admin ? <form onSubmit={e => { e.preventDefault(); void run(() => change(`cases/${selected.id}/assignment`, { version: selected.version, lawyerId: lawyer, reason })); }}>
        <fieldset disabled={busy || ["RECUSADO", "ENCERRADO"].includes(selected.state)}><legend>Atribuir ou transferir responsável</legend>
          <label htmlFor="case-lawyer">Advogado responsável</label><select id="case-lawyer" required value={lawyer} onChange={e => setLawyer(e.target.value)}><option value="">Selecione</option>{lawyers.results.map(row => <option key={row.id} value={row.id}>{row.name || row.email} — {row.email}</option>)}</select>
          {lawyers.nextCursor && <button type="button" onClick={() => void run(async () => { const result = await api<Page<Lawyer>>(`cases/lawyers?cursor=${encodeURIComponent(lawyers.nextCursor!)}`); setLawyers({ results: [...lawyers.results, ...result.results], nextCursor: result.nextCursor }); })}>Mais profissionais</button>}
          <label>Motivo administrativo<textarea required minLength={5} maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label><p>O motivo é registrado em auditoria e não é exibido ao cliente.</p><button disabled={!lawyer || lawyer === selected.lawyerId}>Salvar responsável</button>
        </fieldset>
      </form> : <>
        {client && selected.state === "RASCUNHO" ? <>
          <form onSubmit={save}><fieldset disabled={busy}><legend>Dados do rascunho</legend>
            <label>Título do caso<input maxLength={160} value={title} onChange={e => setTitle(e.target.value)} /></label>
            <label htmlFor="case-category">Categoria</label><select id="case-category" value={category} onChange={e => setCategory(e.target.value)}><option value="">Selecione</option>{catalog?.categories.map(row => <option key={row.id} value={row.id}>{row.label}</option>)}</select>
            <label>Data do ocorrido<input type="date" value={occurredOn} onChange={e => setOccurredOn(e.target.value)} /></label>
            <label>Descrição do que aconteceu<textarea rows={7} maxLength={20000} value={description} onChange={e => setDescription(e.target.value)} /></label>
            <label className="case-check"><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} />Estou ciente de que família e sucessões não fazem parte do serviço.</label>
            <button>Salvar rascunho</button>
          </fieldset></form>
          <p>Salve os dados antes de enviar. Anexe os documentos comprobatórios abaixo e aguarde a verificação. O envio encaminha a ocorrência para análise; não garante aceite.</p>
          <button disabled={busy || !!dirty || !catalog?.submission?.canSubmit || (catalog?.intakeRequired && (!occurredOn || !documents.results.some(file => file.status === "AVAILABLE" && file.uploadedById === user.id)))} onClick={submit}>Enviar ocorrência para análise</button>
        </> : <><h4>{selected.title}</h4><p>{selected.categoryLabel}</p><p>Data do ocorrido: {selected.occurredOn ? selected.occurredOn.split("-").reverse().join("/") : "Não informada"}</p><p className="case-narrative">{selected.description}</p></>}
        {user.role === "LAWYER" && selected.state === "SUBMETIDO" && <button disabled={busy} onClick={() => void run(() => change(`cases/${selected.id}/transitions`, { version: selected.version, targetState: "EM_TRIAGEM" }))}>Iniciar triagem</button>}
        {user.role === "LAWYER" && selected.state === "EM_TRIAGEM" && <fieldset disabled={busy}><legend>Decisão de triagem</legend>
          {["Escopo compatível: trânsito ou civil, exceto família e sucessões", "Conflito de interesses analisado", "Informações suficientes para decidir o atendimento"].map((label, index) => <label key={label} className="case-check"><input type="checkbox" checked={checks[index]} onChange={e => setChecks(old => old.map((value, i) => i === index ? e.target.checked : value))} />{label}</label>)}
          <label>Justificativa visível ao cliente<textarea maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label>
          <div className="case-actions"><button disabled={reason.trim().length < 5 || !checks.every(Boolean)} onClick={() => void run(() => change(`cases/${selected.id}/transitions`, { version: selected.version, targetState: "ACEITO", reason, scopeConfirmed: checks[0], conflictChecked: checks[1], informationSufficient: checks[2] }))}>Aprovar caso e preparar procuração</button>
          <button disabled={reason.trim().length < 5} onClick={() => void run(() => change(`cases/${selected.id}/transitions`, { version: selected.version, targetState: "RECUSADO", reason }))}>Recusar com justificativa</button></div>
          <label>Informações a complementar<textarea maxLength={4000} value={complement} onChange={e => setComplement(e.target.value)} /></label><button disabled={complement.trim().length < 5} onClick={() => void run(() => change(`cases/${selected.id}/requests`, { version: selected.version, description: complement }))}>Solicitar complemento</button>
        </fieldset>}
        {["ACEITO", "AGUARDANDO_PROCURACAO", "EM_PREPARACAO", "EM_ACOMPANHAMENTO", "ENCERRADO"].includes(selected.state) && <LegalWorkflow key={`workflow-${selected.id}`} caseId={selected.id} version={selected.version} user={user} documents={documents.results} onChange={async () => {onChange(); await list(); await load(selected);}} />}
        <CaseProposals key={`proposals-${selected.id}`} caseId={selected.id} version={selected.version} state={selected.state} user={user} onChange={async () => {onChange(); await list(); await load(selected);}} />
        <CaseMessages key={`messages-${selected.id}`} caseId={selected.id} user={user} available={!!selected.lawyerId && !["RASCUNHO", "RECUSADO", "ENCERRADO"].includes(selected.state)} onChange={onChange} />
        <CaseDocuments available={catalog?.documentsAvailable ?? false} key={selected.id} caseId={selected.id} versions={documents.results} busy={busy} readOnly={["RECUSADO", "ENCERRADO"].includes(selected.state)} run={run} refresh={refreshDocuments} hasMore={!!documents.nextCursor} more={async () => {
          const result = await api<Page<DocumentVersion>>(`cases/${selected.id}/documents?cursor=${encodeURIComponent(documents.nextCursor!)}`);
          setDocuments(old => ({ results: [...old.results, ...result.results], nextCursor: result.nextCursor }));
        }} />
        {requests.results.length > 0 && <section><h4>Complementos</h4>{requests.results.map(row => <div className="case-pending" key={row.id}><p className="case-narrative"><strong>Solicitação: </strong>{row.description}</p>{row.response && <p className="case-narrative"><strong>Resposta: </strong>{row.response}</p>}{row.resolved && <p>Conferido: {row.resolution}</p>}
          {row.attachments?.map(item => <button key={item.id} disabled={busy} onClick={() => void run(() => downloadDocument(item))}>Anexo: {item.filename} (v{item.number})</button>)}
          {!row.resolved && client && !row.responded && <form onSubmit={e => { e.preventDefault(); void run(() => change(`cases/${selected.id}/requests/${row.id}/response`, { version: selected.version, text: complement, documentVersionIds: attachments })); }}><fieldset disabled={busy}><label>Sua resposta<textarea required minLength={5} maxLength={10000} value={complement} onChange={e => setComplement(e.target.value)} /></label>
            <p>Selecione os documentos já verificados para acompanhar a resposta.</p>{documents.results.filter(item => item.status === "AVAILABLE" && item.uploadedById === user.id).map(item => <label key={item.id} className="case-check"><input type="checkbox" checked={attachments.includes(item.id)} onChange={e => setAttachments(old => e.target.checked ? [...old, item.id] : old.filter(id => id !== item.id))} />Anexar {item.filename} (v{item.number})</label>)}
            <button>Enviar complemento</button></fieldset></form>}
          {!row.resolved && row.responded && <p>Aguardando conferência pelo responsável.</p>}
          {!row.resolved && row.responded && user.role === "LAWYER" && <form onSubmit={e => { e.preventDefault(); void run(() => change(`cases/${selected.id}/requests/${row.id}/resolve`, { version: selected.version, reason })); }}><fieldset disabled={busy}><label>Resultado da conferência<textarea required minLength={5} maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} /></label><button>Conferir e retomar triagem</button></fieldset></form>}
        </div>)}{requests.nextCursor && <button disabled={busy} onClick={() => void run(async () => { const result = await api<Page<Pending>>(`cases/${selected.id}/requests?cursor=${encodeURIComponent(requests.nextCursor!)}`); setRequests({ results: [...requests.results, ...result.results], nextCursor: result.nextCursor }); })}>Mais complementos</button>}</section>}
        {catalog?.documentsAvailable && <CaseExport key={`export-${selected.id}`} caseId={selected.id} version={selected.version} />}
        <section><h4>Histórico</h4><ol className="case-history">{events.results.map(row => <li key={row.id}><strong>{labels[row.action] || "Atualização do caso"}</strong><time dateTime={row.createdAt}>{new Date(row.createdAt).toLocaleString("pt-BR")}</time>{row.reason && <p className="case-narrative">{row.reason}</p>}</li>)}</ol>
          {events.nextCursor && <button disabled={busy} onClick={() => void run(async () => { const result = await api<Page<Event>>(`cases/${selected.id}/timeline?cursor=${encodeURIComponent(events.nextCursor!)}`); setEvents({ results: [...events.results, ...result.results], nextCursor: result.nextCursor }); })}>Mais eventos</button>}
        </section>
      </>}
    </article>}
  </section>;
}
