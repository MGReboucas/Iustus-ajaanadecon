"use client";

import { useState } from "react";
import { DocumentVersion, downloadDocument, uploadDocument } from "@/lib/api/documents";

type Props = {
  available: boolean; caseId: string; versions: DocumentVersion[]; busy: boolean; readOnly: boolean; hasMore: boolean;
  run: (action: () => Promise<void>) => Promise<void>; refresh: () => Promise<void>; more: () => Promise<void>;
};

export default function CaseDocuments({ available, caseId, versions, busy, readOnly, hasMore, run, refresh, more }: Props) {
  const [file, setFile] = useState<File>();
  const [target, setTarget] = useState("");
  const [inputKey, setInputKey] = useState(0);
  const [message, setMessage] = useState("");
  // Paginação decrescente: a primeira versão vista de cada documento é a mais recente.
  const latest = versions.filter((item, index) => versions.findIndex(row => row.documentId === item.documentId) === index);

  return <section className="case-documents" aria-labelledby="case-documents-title">
    <div className="cases-heading"><h4 id="case-documents-title">Documentos do caso</h4><button disabled={busy} onClick={() => void run(refresh)}>Atualizar documentos</button></div>
    <p>Arquivos compartilhados entre o cliente e o advogado responsável. PDF, JPEG ou PNG, até 20 MiB por arquivo. O download fica disponível após a verificação.</p>
    {!available && <p role="status">O envio de documentos está indisponível neste momento. Você pode salvar o rascunho e completar os anexos quando o serviço estiver disponível.</p>}
    {available && !readOnly && <form onSubmit={event => { event.preventDefault(); if (!file) return; setMessage(""); void run(async () => {
      try {
        await uploadDocument(caseId, file, versions.find(item => item.id === target));
        setFile(undefined); setTarget(""); setInputKey(old => old + 1);
        setMessage("Arquivo recebido. Aguarde a verificação e atualize a lista.");
      } finally { await refresh(); }
    }); }}><fieldset disabled={busy}><legend>Enviar documento</legend>
      <label>Destino do envio<select value={target} onChange={event => setTarget(event.target.value)}><option value="">Novo documento</option>{latest.map(item => <option key={item.id} value={item.id}>Nova versão de {item.filename}</option>)}</select></label>
      <label>Arquivo para anexar<input key={inputKey} type="file" required accept=".pdf,.jpg,.jpeg,.png" onChange={event => setFile(event.target.files?.[0])} /></label>
      <button disabled={!file}>Enviar arquivo</button>
    </fieldset></form>}
    {message && <p role="status">{message}</p>}
    {!versions.length && <p>Nenhum documento enviado neste caso.</p>}
    <ul className="document-list">{versions.map(item => <li key={item.id}>
      <div><strong>{item.filename}</strong><span>Versão {item.number} · {Math.max(1, Math.ceil(item.sizeBytes / 1024))} KiB</span><span className="case-badge">{item.statusLabel}</span></div>
      <button disabled={busy || item.status !== "AVAILABLE"} onClick={() => void run(() => downloadDocument(item))}>Baixar {item.filename} (v{item.number})</button>
      {item.status === "ERROR" && <p>A verificação está indisponível. O arquivo continua bloqueado; a equipe pode acompanhar a falha.</p>}
      {item.status === "REJECTED" && <p>O arquivo não foi liberado. Confira o conteúdo e envie uma nova versão.</p>}
      {item.status === "UPLOADING" && <p>Envio incompleto. Se houve uma interrupção, selecione uma nova versão e envie novamente.</p>}
    </li>)}</ul>
    {hasMore && <button disabled={busy} onClick={() => void run(more)}>Mais documentos</button>}
  </section>;
}
