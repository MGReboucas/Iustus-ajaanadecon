"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import { DocumentVersion, downloadDocument } from "@/lib/api/documents";
type Template = {id: string; name: string; number: number; body: string; fields: {key: string; label: string}[]};
export default function MandateGenerator({caseId, version, lawyerName, onGenerated}: {caseId: string; version: number; lawyerName: string; onGenerated: (file: DocumentVersion) => Promise<void>}) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [previous, setPrevious] = useState("");
  const [approved, setApproved] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [generated, setGenerated] = useState<DocumentVersion>();
  const template = templates.find(row => row.id === selected);
  async function load(next?: string) {
    const result = await api<{results: Template[]; nextCursor: string | null}>(`legal/mandate-templates${next ? `?cursor=${encodeURIComponent(next)}` : ""}`);
    setTemplates(old => next ? [...old, ...result.results] : result.results); setCursor(result.nextCursor);
  }
  useEffect(() => {load().catch(e => setError(e.message));}, []);
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try {await action();} catch(e) {setError(e instanceof Error ? e.message : "Não foi possível concluir.");} finally {setBusy(false);}
  }
  function select(row: Template) {setSelected(row.id); setValues(Object.fromEntries(row.fields.map(field => [field.key, field.key === "advogado_nome" ? lawyerName : ""]))); setConfirmed(false);}
  return <section className="mandate-generator"><h5>Gerar procuração em PDF</h5><p>Use um modelo jurídico revisado por você. O PDF gerado ficará nos documentos do caso e poderá ser selecionado para solicitar a assinatura.</p>
    {error && <p role="alert" className="dashboard-error">{error}</p>}{message && <p role="status">{message}</p>}
    <details><summary>Cadastrar ou revisar modelo</summary><form onSubmit={event => {event.preventDefault(); void run(async () => {
      const row = await api<Template>("legal/mandate-templates", {name, body, approved, ...(previous ? {previousId: previous} : {})});
      setTemplates(old => [row, ...old]); select(row); setPrevious(""); setApproved(false); setMessage("Modelo aprovado e salvo como nova versão.");
    });}}><fieldset disabled={busy}><legend>{previous ? "Nova versão do modelo" : "Novo modelo"}</legend>
      <label>Nome do modelo<input required minLength={3} maxLength={160} value={name} onChange={e => setName(e.target.value)} /></label>
      <label>Texto jurídico do modelo<textarea required minLength={40} maxLength={30000} rows={9} value={body} onChange={e => setBody(e.target.value)} /></label>
      <p>Campos obrigatórios: <code>{"{{cliente_nome}}, {{advogado_nome}}, {{advogado_oab}}"}</code>.</p><p>Também disponíveis: <code>{"{{cliente_documento}}, {{cliente_endereco}}, {{advogado_endereco}}, {{cidade}}, {{data_emissao}}, {{caso_referencia}}"}</code>. Data de emissão e referência são preenchidas pelo sistema.</p>
      <label className="case-check"><input type="checkbox" required checked={approved} onChange={e => setApproved(e.target.checked)} />Revisei e aprovo o texto e os poderes deste modelo</label><button disabled={!approved}>Salvar modelo aprovado</button>
      {previous && <button type="button" onClick={() => {setPrevious(""); setName(""); setBody(""); setApproved(false);}}>Cancelar revisão</button>}
    </fieldset></form></details>
    <label>Modelo de procuração<select disabled={busy} value={selected} onChange={e => {const row = templates.find(item => item.id === e.target.value); if(row) select(row); else setSelected("");}}><option value="">Selecione um modelo aprovado</option>{templates.map(row => <option key={row.id} value={row.id}>{row.name} · v{row.number}</option>)}</select></label>
    {cursor && <button disabled={busy} onClick={() => void run(() => load(cursor))}>Mais modelos</button>}
    {template && <>
      <details><summary>Conferir texto do modelo v{template.number}</summary><p className="case-narrative">{template.body}</p><button disabled={busy} onClick={() => {setPrevious(template.id); setName(template.name); setBody(template.body); setApproved(false); setMessage("Abra Cadastrar ou revisar modelo para salvar a nova versão.");}}>Criar nova versão deste modelo</button></details>
      <form onSubmit={event => {event.preventDefault(); void run(async () => {
        const result = await api<{document: DocumentVersion}>(`cases/${caseId}/mandates`, {version, templateId: template.id, fields: values, confirmed});
        setGenerated(result.document); setConfirmed(false); await onGenerated(result.document); setMessage("Procuração gerada. Baixe e confira o PDF antes de solicitar a assinatura.");
      });}}><fieldset disabled={busy}><legend>Dados da procuração</legend>{template.fields.map(field => <label key={field.key}>{field.label}<input required maxLength={500} value={values[field.key] || ""} onChange={e => setValues(old => ({...old, [field.key]: e.target.value}))} /></label>)}
        <label className="case-check"><input type="checkbox" required checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Conferi os dados e o modelo para este caso</label><button disabled={!confirmed}>Gerar PDF da procuração</button>
      </fieldset></form>
    </>}
    {generated && <button disabled={busy} onClick={() => void run(() => downloadDocument(generated))}>Baixar procuração gerada</button>}
  </section>;
}
