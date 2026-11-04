"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { SubscriptionState } from "../../../contracts/api";

export default function SubscriptionSettings() {
  const [data, setData] = useState<SubscriptionState>();
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { let active = true; api<SubscriptionState>("billing/subscription").then(value => { if (active) setData(value); }).catch(() => { if (active) setError("Não foi possível consultar sua renovação."); }); return () => { active = false; }; }, []);
  async function cancel() {
    if (!confirmed || busy) return;
    setBusy(true); setError("");
    try { setData(await api<SubscriptionState>("billing/subscription", { cancelRenewal: true })); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível cancelar."); }
    finally { setBusy(false); }
  }
  return <section className="dashboard-card"><h2>Renovação da associação</h2>{error && <p role="alert">{error}</p>}
    {data?.subscription ? <><p>{data.subscription.automaticRenewal ? "Renovação automática ativa" : data.subscription.canceledAt ? "Próxima renovação cancelada" : "Renovação em conferência"}</p>
      <p>{data.subscription.installments} parcelas de {(data.subscription.amount / data.subscription.installments / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} por ciclo anual.</p>
      {data.subscription.nextChargeAt && <p>Próxima cobrança: {new Date(data.subscription.nextChargeAt).toLocaleDateString("pt-BR")}.</p>}
      {!data.subscription.canceledAt && <><label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Quero cancelar a próxima renovação automática.</label><button disabled={busy || !confirmed} onClick={cancel}>{busy ? "Cancelando…" : "Cancelar próxima renovação"}</button></>}
      <p>O cancelamento impede novas renovações. Mantém a vigência já paga e o histórico dos seus casos. Uma cobrança já iniciada precisa de atendimento para eventual estorno.</p></> : data && <p>Não há renovação automática cadastrada.</p>}
  </section>;
}
