"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, ApiError, Portal, Profile } from "@/lib/api/client";
import "./dashboard.css";
import CasesWorkspace from "./CasesWorkspace";
import Brand from "./Brand";
import DashboardOverview from "./DashboardOverview";
import ServiceAccess from "./ServiceAccess";
import AccountSettings from "./AccountSettings";
import AccountManagement from "./AccountManagement";

export default function Dashboard({ portal }: { portal: Portal }) {
  const [user, setUser] = useState<Profile>();
  const [manualAdmission, setManualAdmission] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [openCase, setOpenCase] = useState<{ id: string; sequence: number }>();
  useEffect(() => {
    api<{ user: Profile; manualAdmissionAvailable?: boolean }>(`dashboard/${portal}`).then(result => { setUser(result.user); setManualAdmission(!!result.manualAdmissionAvailable); }).catch(reason => {
      if (reason instanceof ApiError && reason.code === "AUTH_REQUIRED") window.location.replace("/acessar");
      else setError(reason.message);
    });
  }, [portal]);
  async function leave() {
    setBusy(true); setError("");
    try { await api("auth/logout", {}); window.location.replace("/acessar"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível sair."); setBusy(false); }
  }
  async function invite(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const result = await api<{ message: string }>("admin/invitations", { email }); setMessage(result.message); setEmail(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível enviar o convite."); }
    finally { setBusy(false); }
  }
  return <main className="dashboard">
    <header><div className="dashboard-brand"><Brand /><span>{portal === "team" ? "Portal profissional" : "Área do associado"}</span></div>{user && <button disabled={busy} onClick={leave}>Sair da conta</button>}</header>
    {error && <p role="alert" className="dashboard-error">{error}</p>}
    {!user && !error && <p role="status">Carregando seu acesso…</p>}
    {user && <>
      <section className="dashboard-welcome"><p>{portal === "team" ? "ATENDIMENTO DA ASSOCIAÇÃO" : "SEU ATENDIMENTO JURÍDICO"}</p><h1>Olá, {user.name || "bem-vindo"}.</h1><p>{portal === "team" ? "Acompanhe a fila, confira pendências e mantenha seus clientes informados." : "Cadastre ocorrências, assine a procuração dos casos aprovados e acompanhe o trabalho do seu advogado."}</p><nav className="dashboard-nav" aria-label="Atalhos do painel"><a href="#resumo">Visão geral</a><a href="#meus-casos">{user.role === "ADMIN" ? "Distribuição" : "Casos"}</a><a href="#minha-conta">Minha conta</a></nav></section>
      <div id="resumo"><DashboardOverview user={user} revision={revision} openCase={id => setOpenCase({ id, sequence: Date.now() })} /></div>
      {user.role === "ADMIN" && manualAdmission && <ServiceAccess />}
      <CasesWorkspace user={user} openCase={openCase} onChange={() => setRevision(value => value + 1)} />
      <div id="minha-conta" className="dashboard-account">
      <div className="dashboard-grid">
        <AccountSettings user={user} onChange={setUser} />
        {portal === "team" && user.role === "ADMIN" && <section className="dashboard-card"><h2>Aprovar profissional</h2><p>A aprovação registra o profissional e envia um link para confirmar o e-mail e definir a senha. Use o mesmo e-mail para reenviar uma ativação pendente.</p><form onSubmit={invite}><label>E-mail do profissional<input required type="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} /></label><button disabled={busy}>Aprovar e enviar ativação</button></form>{message && <p role="status">{message}</p>}</section>}
      </div>
      <AccountManagement admin={user.role === "ADMIN"} />
      </div>
    </>}
  </main>;
}
