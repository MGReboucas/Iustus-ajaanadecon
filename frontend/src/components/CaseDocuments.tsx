"use client";

import { useEffect, useRef, useState } from "react";
import { DocumentVersion, downloadDocument, uploadDocument, removeDocument } from "@/lib/api/documents";

type Props = {
  intake?: boolean; demo?: boolean; available: boolean; caseId: string; versions: DocumentVersion[]; busy: boolean; readOnly: boolean; hasMore: boolean;
  run: (action: () => Promise<void>) => Promise<void>; refresh: () => Promise<void>; more: () => Promise<void>;
};

export default function CaseDocuments({ intake = false, demo = false, available, caseId, versions, busy, readOnly, hasMore, run, refresh, more }: Props) {
  const [uploadingName, setUploadingName] = useState("");
  const uploading = useRef(false);
  const [target, setTarget] = useState("");
  const [message, setMessage] = useState("");
  const pending = versions.some(item => ["QUARANTINED", "SCANNING", "ERROR"].includes(item.status));
  useEffect(() => {
    if (demo || !available || busy || !pending) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void run(refresh);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [demo, available, busy, pending, versions, run, refresh]);
  // Paginação decrescente: a primeira versão vista de cada documento é a mais recente.
  const latest = versions.filter((item, index) => versions.findIndex(row => row.documentId === item.documentId) === index);

  function selectFiles(files: File[]) {
    if (!files.length || busy || uploading.current) return;
    uploading.current = true;
    setUploadingName(files[0].name);
    setMessage("");
    void run(async () => {
      try {
        if (target && files.length > 1) throw new Error("Selecione um arquivo por nova versão.");
        const failures: string[] = [];
        for (const [index, file] of files.entries()) {
          setUploadingName(`${file.name} (${index + 1}/${files.length})`);
          try {
            if (demo && file.size > 3 * 1024 * 1024) throw new Error("Na demonstração, use arquivos de até 3 MiB.");
            await uploadDocument(caseId, file, versions.find(item => item.id === target));
          } catch (error) {
            failures.push(`${file.name}: ${error instanceof Error ? error.message : "Não foi possível enviar."}`);
          }
        }
        setTarget("");
        if (failures.length) throw new Error(failures.join(" "));
        setMessage(demo ? "Arquivos de demonstração recebidos, sem verificação por antivírus." : "Arquivos recebidos. A verificação será atualizada automaticamente.");
      } finally {
        try { await refresh(); }
        finally { uploading.current = false; setUploadingName(""); }
      }
    });
  }

  return <section className="case-documents" aria-labelledby="case-documents-title">
    <div className="cases-heading"><h4 id="case-documents-title">{intake ? "Documentos comprobatórios" : "Documentos do caso"}</h4><button disabled={busy} onClick={() => void run(refresh)}>Atualizar documentos</button></div>
    {demo && <p role="status"><strong>Demonstração restrita: use apenas arquivos fictícios, até 3 MiB.</strong> Não há verificação por antivírus. Os anexos não liberam o envio da ocorrência para análise.</p>}
    <p>Arquivos compartilhados entre o cliente e o advogado responsável. PDF, JPEG ou PNG, até {demo ? "3" : "20"} MiB por arquivo. {demo ? "Download de teste, sem verificação por antivírus." : "O download fica disponível após a verificação."}</p>
    {!available && <p role="status">O envio de documentos está indisponível neste momento. Você pode salvar o rascunho e completar os anexos quando o serviço estiver disponível.</p>}
    <div className="document-box">
    {available && !readOnly && <fieldset disabled={busy || !!uploadingName} aria-label="Anexar documentos">
      {!intake && <label>Destino do envio<select value={target} onChange={event => setTarget(event.target.value)}><option value="">Novo documento</option>{latest.map(item => <option key={item.id} value={item.id}>Nova versão de {item.filename}</option>)}</select></label>}
      <label className="document-picker">
        <input aria-label="Arquivo para anexar" type="file" multiple={!target} accept=".pdf,.jpg,.jpeg,.png" onChange={event => {
          const files = Array.from(event.target.files || []);
          event.target.value = "";
          selectFiles(files);
        }} />
        <span aria-hidden="true"><span className="document-picker-plus">+</span> {target ? "Escolher arquivo" : "Adicionar arquivos"}</span>
        <small>O envio começa automaticamente ao selecionar.</small>
      </label>
    </fieldset>}
    {uploadingName && <p role="status">Enviando {uploadingName}…</p>}
    {message && <p role="status">{message}</p>}
    {!versions.length && <p>Nenhum documento enviado neste caso.</p>}
    <ul className="document-list document-chips" aria-label="Arquivos anexados">{versions.map(item => <li key={item.id}>
      <button type="button" className="document-file" aria-label={`Baixar ${item.filename} (v${item.number})`} title={`${item.filename} · Versão ${item.number} · ${Math.max(1, Math.ceil(item.sizeBytes / 1024))} KiB · ${item.statusLabel}`} disabled={busy || (item.status !== "AVAILABLE" && !(demo && item.status === "DEMO_UNVERIFIED"))} onClick={() => void run(() => downloadDocument(item))}>
        <span className="document-filename">{item.filename}</span>
        {item.status !== "AVAILABLE" && <small>{item.statusLabel}</small>}
      </button>
      {intake && !readOnly && <button type="button" className="document-remove" aria-label={`Remover ${item.filename} (v${item.number})`} title="Remover anexo" disabled={busy} onClick={() => void run(async () => {
        await removeDocument(item);
        setMessage("Anexo removido do rascunho.");
        await refresh();
      })}><span aria-hidden="true">×</span></button>}
    </li>)}</ul>
    {versions.some(item => ["ERROR", "REJECTED", "UPLOADING"].includes(item.status)) && <p className="document-picker-hint">Arquivos com falha ou recusados continuam bloqueados. Remova o anexo e tente enviá-lo novamente.</p>}
    {hasMore && <button disabled={busy} onClick={() => void run(more)}>Mais documentos</button>}
    </div>
  </section>;
}
