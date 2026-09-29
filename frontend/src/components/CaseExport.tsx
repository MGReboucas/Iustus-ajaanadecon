"use client";
import { useState } from "react";
import { api } from "@/lib/api/client";
type Export = {url: string; filename: string; expiresAt: string; sha256: string};
export default function CaseExport({caseId, version}: {caseId: string; version: number}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [bundle, setBundle] = useState<Export>();
  async function generate() {
    setBusy(true); setError(""); setBundle(undefined);
    try {setBundle(await api<Export>(`cases/${caseId}/exports`, {version}));}
    catch(e) {setError(e instanceof Error ? e.message : "Não foi possível preparar o dossiê.");}
    finally {setBusy(false);}
  }
  async function download() {
    if(!bundle) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(bundle.url, {credentials: "same-origin", cache: "no-store"});
      if(!response.ok) {const result = await response.json().catch(() => null); throw new Error(result?.error?.message || "Não foi possível baixar o dossiê.");}
      const content = await response.arrayBuffer();
      const hash = await crypto.subtle.digest("SHA-256", content);
      const hex = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
      if(hex !== bundle.sha256) throw new Error("O download está incompleto. Gere o dossiê novamente.");
      const url = URL.createObjectURL(new Blob([content], {type: "application/zip"}));
      const link = document.createElement("a"); link.href = url; link.download = bundle.filename;
      document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch(e) {setError(e instanceof Error ? e.message : "Falha no download.");} finally {setBusy(false);}
  }
  return <section className="case-export"><h4>Cópia do caso</h4><p>Prepare um ZIP com documentos liberados, peças publicadas, mensagens e histórico compartilhado. Arquivos em verificação ficam indicados no manifesto.</p>
    <button disabled={busy} onClick={() => void generate()}>{busy ? "Preparando…" : "Preparar dossiê"}</button>
    {error && <p role="alert" className="dashboard-error">{error}</p>}
    {bundle && <div><p role="status">Dossiê preparado. Download disponível até {new Date(bundle.expiresAt).toLocaleTimeString("pt-BR")} nesta sessão.</p><button disabled={busy} onClick={() => void download()}>Baixar dossiê ZIP</button></div>}
  </section>;
}
