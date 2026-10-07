"use client";

import { api, ApiError, Context } from "./client";

export type { DocumentVersion } from '../../../../contracts/api';
import type { DocumentVersion, DocumentUpload as Upload, DirectUpload } from '../../../../contracts/api';

export async function uploadDocument(caseId: string, file: File, previous?: DocumentVersion) {
  if (!file.size || file.size > 20 * 1024 * 1024) throw new Error("Escolha um arquivo de até 20 MiB, com conteúdo.");
  const extension = file.name.split(".").pop()?.toLowerCase();
  const mime = extension === "pdf" ? "application/pdf" : extension === "png" ? "image/png" :
    extension === "jpg" || extension === "jpeg" ? "image/jpeg" : undefined;
  if (!mime) throw new Error("Escolha um arquivo PDF, JPEG ou PNG.");
  const buffer = await file.arrayBuffer();
  const hash = await crypto.subtle.digest("SHA-256", buffer);
  const checksum = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
  const upload = await api<Upload>(previous ? `documents/${previous.documentId}/versions` : `cases/${caseId}/documents/uploads`,
    { filename: file.name, sizeBytes: file.size, mime, ...(previous ? { previousVersion: previous.number } : {}) });
  let response: Response;
  if (upload.directUpload) {
    const authorization = await api<DirectUpload>(`uploads/${upload.uploadId}/authorize`, { checksum });
    // Nenhum cookie de sessão, CSRF ou credencial permanente é enviado ao bucket.
    response = await fetch(authorization.url, { method: authorization.method, credentials: "omit",
      cache: "no-store", redirect: "error", referrerPolicy: "no-referrer",
      headers: authorization.headers, body: buffer });
  } else {
    const { csrfToken } = await api<Context>("auth/csrf");
    response = await fetch(upload.uploadUrl, { method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/octet-stream", "X-CSRFToken": csrfToken }, body: buffer });
  }
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new ApiError(result?.error?.code || "UPLOAD_FAILED", result?.error?.message || "O envio falhou. Atualize a lista e tente uma nova versão.");
  }
  return api<DocumentVersion>(`uploads/${upload.uploadId}/complete`, { checksum });
}

export async function downloadDocument(item: DocumentVersion) {
  const { url } = await api<{ url: string }>(`documents/${item.documentId}/versions/${item.id}/download`);
  const response = await fetch(url, { credentials: "same-origin", cache: "no-store" });
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new ApiError(result?.error?.code || "DOWNLOAD_FAILED", result?.error?.message || "Não foi possível baixar o arquivo.");
  }
  const local = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = local; link.download = item.filename;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(local), 10000);
}
