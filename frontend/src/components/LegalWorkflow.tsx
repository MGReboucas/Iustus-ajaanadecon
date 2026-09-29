"use client";
import { useEffect, useState } from "react";
import { api, Profile } from "@/lib/api/client";
import { DocumentVersion, downloadDocument } from "@/lib/api/documents";
type Task = {id: string; kind: string; title: string; dueAt: string; completedAt: string | null; outcome: string};
type Workflow = {version: number; state: string; scope: string; position: string; processNumber: string; authority: string; draft?: string; publishedText: string; protocol: string; mandate: DocumentVersion | null; signedMandate: DocumentVersion | null; receipt: DocumentVersion | null; tasks: Task[]};
type Props = {caseId: string; version: number; user: Profile; documents: DocumentVersion[]; onChange: () => Promise<void>};
const kinds: Record<string, string> = {DEADLINE: "Prazo", HEARING: "Audiência", STAGE: "Etapa"};
export default function LegalWorkflow({caseId, version, user, documents, onChange}: Props) {
  const [work, setWork] = useState<Workflow>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [text, setText] = useState("");
  const [scope, setScope] = useState("");
  const [draft, setDraft] = useState("");
  const [position, setPosition] = useState("APPLICANT");
  const [authority, setAuthority] = useState("");
  const [processNumber, setProcess] = useState("");
  const [protocol, setProtocol] = useState("");
  const [documentId, setDocument] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("DEADLINE");
  const [dueAt, setDue] = useState("");
  const lawyer = user.role === "LAWYER";
  useEffect(() => {
    let current = true; setBusy(true); setError("");
    api<Workflow>(`cases/${caseId}/workflow`).then(result => {
      if (!current) return;
      setWork(result); setDraft(result.draft || ""); setScope(result.scope); setAuthority(result.authority); setProcess(result.processNumber); setProtocol(result.protocol);
    }).catch(e => {if(current) {setError(e.message); setWork(undefined);}}).finally(() => {if(current) setBusy(false);});
    return () => {current = false;};
  }, [caseId, version, refresh]);
  async function act(action: string, extra: object = {}) {
    if (!work) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api<Workflow>(`cases/${caseId}/workflow`, {version: work.version, action, ...extra});
      setWork(result); setText(""); setConfirmed(false); setDocument(""); setMessage("Etapa registrada."); await onChange();
    } catch(e) {setError(e instanceof Error ? e.message : "Não foi possível registrar a etapa.");}
    finally {setBusy(false);}
  }
  async function download(file: DocumentVersion) {
    setBusy(true); setError("");
    try {await downloadDocument(file);} catch(e) {setError(e instanceof Error ? e.message : "Falha no download.");} finally {setBusy(false);}
  }
  const fileSelect = <label>Documento verificado<select value={documentId} onChange={e => setDocument(e.target.value)}><option value="">Selecione um arquivo enviado por você</option>{documents.filter(file => file.status === "AVAILABLE" && file.uploadedById === user.id).map(file => <option key={file.id} value={file.id}>{file.filename} · v{file.number}</option>)}</select><small>Envie o arquivo na seção Documentos do caso e aguarde a verificação. Use Mais documentos se necessário.</small></label>;
  return <section className="legal-workflow"><div className="cases-heading"><h4>Atendimento e andamento</h4><button disabled={busy} onClick={() => setRefresh(n => n + 1)}>Atualizar andamento</button></div>
    {error && <p role="alert" className="dashboard-error">{error}</p>}{message && <p role="status">{message}</p>}{busy && <p role="status">Atualizando atendimento…</p>}
    {work && <>
      {work.scope && <div><h5>Etapas contratadas</h5><p className="case-narrative">{work.scope}</p><p>Posição: {{AUTHOR: "Autor", DEFENDANT: "Réu", APPLICANT: "Requerente"}[work.position]}</p></div>}
      {work.authority && <p>Órgão: {work.authority} · Processo: {work.processNumber || "Ainda não informado"}</p>}
      <div className="case-actions">{work.mandate && <button disabled={busy} onClick={() => void download(work.mandate!)}>Baixar procuração</button>}{work.signedMandate && <button disabled={busy} onClick={() => void download(work.signedMandate!)}>Baixar procuração devolvida</button>}{work.receipt && <button disabled={busy} onClick={() => void download(work.receipt!)}>Baixar comprovante de protocolo</button>}</div>
      {work.protocol && <p>Protocolo registrado: {work.protocol}</p>}
      {work.publishedText && <details open><summary>Peça revisada disponibilizada</summary><p className="case-narrative">{work.publishedText}</p></details>}
      {work.state === "ENCERRADO" ? <p>Atendimento encerrado. Documentos e histórico continuam disponíveis.</p> : <fieldset disabled={busy}>
        <legend>{lawyer ? "Conduzir atendimento" : "Sua próxima ação"}</legend>
        {lawyer && work.state === "ACEITO" && <>
          <label>Etapas contratadas<textarea value={scope} onChange={e => setScope(e.target.value)} maxLength={50000} /></label>
          <label>Posição do cliente<select value={position} onChange={e => setPosition(e.target.value)}><option value="APPLICANT">Requerente</option><option value="AUTHOR">Autor</option><option value="DEFENDANT">Réu</option></select></label>
          <label>Órgão responsável<input value={authority} onChange={e => setAuthority(e.target.value)} maxLength={200} /></label><label>Número do processo<input value={processNumber} onChange={e => setProcess(e.target.value)} maxLength={100} /></label>
          {fileSelect}<button disabled={!documentId || scope.trim().length < 10} onClick={() => void act("START", {text: scope, position, authority, processNumber, documentId})}>Solicitar procuração</button>
        </>}
        {work.state === "AGUARDANDO_PROCURACAO" && (lawyer ? <><p>{work.signedMandate ? "Confira o arquivo devolvido antes de iniciar a preparação." : "Aguardando a devolução da procuração pelo cliente."}</p><label className="case-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Conferi a procuração assinada</label><button disabled={!work.signedMandate || !confirmed} onClick={() => void act("VERIFY", {confirmed})}>Confirmar procuração</button><label>Ajuste necessário na procuração<textarea value={text} onChange={e => setText(e.target.value)} /></label><button disabled={!work.signedMandate || text.trim().length < 5} onClick={() => void act("RETURN_MANDATE", {text})}>Solicitar correção da procuração</button></> : <><p>Baixe a procuração, assine conforme orientação do advogado e envie o arquivo em Documentos do caso. Depois, selecione a versão verificada abaixo.</p>{fileSelect}<button disabled={!documentId} onClick={() => void act("SIGN", {documentId})}>Entregar procuração assinada</button></>)}
        {lawyer && ["EM_PREPARACAO", "EM_ACOMPANHAMENTO"].includes(work.state) && <>
          <label>Minuta interna da peça<textarea rows={10} value={draft} onChange={e => setDraft(e.target.value)} maxLength={50000} /></label><p>A minuta fica restrita ao advogado responsável até a publicação.</p>
          <button disabled={draft.trim().length < 10} onClick={() => void act("DRAFT", {text: draft})}>Salvar minuta</button>
          <label className="case-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Revisei os dados e confirmo a ação selecionada</label>
          <button disabled={!confirmed || !work.draft || draft !== work.draft} onClick={() => void act("PUBLISH", {confirmed})}>Publicar peça revisada</button>
          <label>Órgão do protocolo<input value={authority} onChange={e => setAuthority(e.target.value)} maxLength={200} /></label><label>Número do processo<input value={processNumber} onChange={e => setProcess(e.target.value)} maxLength={100} /></label><label>Número do protocolo<input value={protocol} onChange={e => setProtocol(e.target.value)} maxLength={200} /></label>
          {fileSelect}<button disabled={!confirmed || !documentId || !protocol || !authority || !work.publishedText} onClick={() => void act("FILE", {confirmed, authority, processNumber, protocol, documentId})}>Registrar protocolo externo</button>
        </>}
        {lawyer && <>
          <label>Movimentação, motivo ou resultado<textarea value={text} onChange={e => setText(e.target.value)} maxLength={50000} /></label><button disabled={text.trim().length < 5} onClick={() => void act("UPDATE", {text})}>Publicar movimentação</button>
          <h5>Agenda e etapas</h5><label>Tipo de compromisso<select value={kind} onChange={e => setKind(e.target.value)}><option value="DEADLINE">Prazo</option><option value="HEARING">Audiência</option><option value="STAGE">Etapa contratada</option></select></label><label>Título do compromisso<input value={title} onChange={e => setTitle(e.target.value)} maxLength={200} /></label><label>Data do compromisso<input type="datetime-local" value={dueAt} onChange={e => setDue(e.target.value)} /></label>
          <button disabled={!title || !dueAt || text.trim().length < 5} onClick={() => void act("TASK", {kind, title, dueAt: new Date(dueAt).toISOString(), text})}>Adicionar compromisso</button>
          {["EM_PREPARACAO", "EM_ACOMPANHAMENTO"].includes(work.state) && <button disabled={!confirmed || text.trim().length < 10 || work.tasks.some(task => !task.completedAt)} onClick={() => void act("CLOSE", {confirmed, text})}>Encerrar atendimento</button>}
        </>}
        {!lawyer && !["AGUARDANDO_PROCURACAO"].includes(work.state) && <p>O advogado está conduzindo esta etapa. Você pode acompanhar as atualizações e conversar na seção de mensagens.</p>}
      </fieldset>}
      <h5>Prazos, audiências e etapas</h5>{work.tasks.length === 0 && <p>Nenhum compromisso registrado.</p>}
      <ul className="legal-tasks">{work.tasks.map(task => <li key={task.id}><strong>{kinds[task.kind]}: {task.title}</strong><p>{new Date(task.dueAt).toLocaleString("pt-BR")} · {task.completedAt ? "Concluído" : new Date(task.dueAt) < new Date() ? "Vencido — requer atenção" : "Pendente"}</p>{task.outcome && <p>{task.outcome}</p>}{lawyer && !task.completedAt && work.state !== "ENCERRADO" && <div className="case-actions"><button disabled={busy || text.trim().length < 5} onClick={() => void act("COMPLETE", {taskId: task.id, text})}>Concluir compromisso</button><button disabled={busy || !dueAt || text.trim().length < 5} onClick={() => void act("RESCHEDULE", {taskId: task.id, text, dueAt: new Date(dueAt).toISOString()})}>Remarcar compromisso</button></div>}</li>)}</ul>
    </>}
  </section>;
}
