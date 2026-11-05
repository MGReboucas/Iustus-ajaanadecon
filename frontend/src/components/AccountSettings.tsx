"use client";
import SubscriptionSettings from "./SubscriptionSettings";
import { FormEvent, useState } from "react";
import { api, Profile } from "@/lib/api/client";
export default function AccountSettings({ user, onChange }: { user: Profile; onChange: (user: Profile) => void }) {
  const [name, setName] = useState(user.name);
  const [enabled, setEnabled] = useState(user.caseEmailEnabled);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const dirty = name !== user.name || enabled !== user.caseEmailEnabled;
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const result = await api<{ user: Profile }>("me", { name, caseEmailEnabled: enabled }, { method: "PATCH" }); onChange(result.user); setMessage("Preferências salvas."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível salvar."); }
    finally { setBusy(false); }
  }
  return <><section className="dashboard-card profile-card"><div className="profile-summary"><span className="profile-avatar" aria-hidden="true">{user.name.trim().slice(0, 1).toUpperCase() || "A"}</span><div><h2>Seu perfil</h2><p>{user.email}</p></div></div><form onSubmit={save}>
    <label>Nome de exibição<input required minLength={2} maxLength={150} value={name} onChange={e => setName(e.target.value)} /></label>
    <label className="account-preference"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Receber avisos do atendimento por e-mail</label>
    <p className="dashboard-note">Os avisos no painel continuam disponíveis. E-mails de acesso e recuperação da conta não são afetados.</p>
    <div className="profile-save"><button disabled={busy || !dirty}>{busy ? "Salvando…" : "Salvar perfil"}</button>{dirty && <span role="status">Alterações ainda não salvas</span>}</div>
  </form>{message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}</section>{user.role === "CLIENT" && <SubscriptionSettings />}</>;
}
