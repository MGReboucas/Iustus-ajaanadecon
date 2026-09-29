"use client";
import { FormEvent, useState } from "react";
import { api, Profile } from "@/lib/api/client";
export default function AccountSettings({ user, onChange }: { user: Profile; onChange: (user: Profile) => void }) {
  const [name, setName] = useState(user.name);
  const [enabled, setEnabled] = useState(user.caseEmailEnabled);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const result = await api<{ user: Profile }>("me", { name, caseEmailEnabled: enabled }, { method: "PATCH" }); onChange(result.user); setMessage("Preferências salvas."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível salvar."); }
    finally { setBusy(false); }
  }
  return <section className="dashboard-card"><h2>Seu perfil</h2><p>{user.email}</p><form onSubmit={save}>
    <label>Nome de exibição<input required minLength={2} maxLength={150} value={name} onChange={e => setName(e.target.value)} /></label>
    <label className="account-preference"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Receber avisos do atendimento por e-mail</label>
    <p>Os avisos no painel continuam disponíveis. E-mails de acesso e recuperação da conta não são afetados.</p>
    <button disabled={busy}>{busy ? "Salvando…" : "Salvar perfil"}</button>
  </form>{message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}</section>;
}
