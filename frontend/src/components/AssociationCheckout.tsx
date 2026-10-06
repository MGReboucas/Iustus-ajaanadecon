"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import Brand from "./Brand";
import { api } from "@/lib/api/client";

type Plan = { amount: number; available: boolean; sandbox: boolean };
const money = (value: number) => (value / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const statuses: Record<string, string> = {
  CREATING: "Preparando seu pagamento.", WAITING: "Aguardando confirmação do pagamento.",
  PAID: "Pagamento confirmado! Enviamos as instruções de acesso para o e-mail informado no PagBank.",
  DECLINED: "O pagamento não foi aprovado. Você pode tentar novamente.",
  CANCELED: "O pagamento foi cancelado. Você pode iniciar uma nova tentativa.",
  EXPIRED: "O prazo deste pagamento terminou. Você pode iniciar uma nova tentativa.",
  REVOKED: "O pagamento foi estornado ou cancelado. Entre na sua conta para consultar seus casos anteriores.",
};

export default function AssociationCheckout() {
  const [plan, setPlan] = useState<Plan>();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [returning, setReturning] = useState(false);
  const [checkoutReady, setCheckoutReady] = useState(false);
  const requestKey = useRef("");
  useEffect(() => {
    let current = true;
    api<Plan>("billing/plan").then(data => { if (current) setPlan(data); }).catch(e => { if (current) setError(e.message); });
    const isReturn = new URLSearchParams(window.location.search).has("retorno");
    setReturning(isReturn);
    requestKey.current = sessionStorage.getItem("iustus-checkout-key") || crypto.randomUUID();
    sessionStorage.setItem("iustus-checkout-key", requestKey.current);
    // Uma nova visita após a conclusão pode ser uma renovação. Repetições de
    // pagamentos ainda pendentes continuam usando a mesma chave.
    api<{status: string}>("billing/checkout").then(data => {
      if (current && !isReturn && ["PAID", "DECLINED", "CANCELED", "EXPIRED", "REVOKED"].includes(data.status)) {
        requestKey.current = crypto.randomUUID();
        sessionStorage.setItem("iustus-checkout-key", requestKey.current);
      }
    }).catch(() => {}).finally(() => { if (current) setCheckoutReady(true); });
    return () => { current = false; };
  }, []);
  useEffect(() => {
    if (!returning) return;
    let current = true;
    const check = () => api<{status: string}>("billing/checkout").then(data => { if (current) { setStatus(data.status); setError(""); } })
      .catch(() => { if (current) setError("Não foi possível consultar este pagamento. A confirmação e as instruções de acesso também serão enviadas por e-mail."); });
    void check();
    const interval = setInterval(() => { if (!document.hidden) void check(); }, 10000);
    return () => { current = false; clearInterval(interval); };
  }, [returning]);
  async function pay(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = await api<{paymentUrl: string}>("billing/checkout", { accepted }, { idempotencyKey: requestKey.current });
      window.location.assign(result.paymentUrl);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível iniciar o pagamento."); setBusy(false); }
  }
  function retry() {
    requestKey.current = crypto.randomUUID(); sessionStorage.setItem("iustus-checkout-key", requestKey.current);
    setReturning(false); setStatus(""); setError(""); window.history.replaceState(null, "", "/checkout");
  }
  return <main className="checkout-page">
    <header className="checkout-header"><div className="checkout-container"><Link href="/" className="checkout-logo" aria-label="Voltar para a Iustus"><Brand decorative /></Link><Link href="/acessar" className="back-link">Já sou associado</Link></div></header>
    <div className="checkout-container checkout-layout">
      <section className="checkout-form-wrap" aria-labelledby="checkout-title">
        <div className="checkout-heading"><span className="checkout-kicker">ASSOCIAÇÃO IUSTUS</span><h1 id="checkout-title">Seu primeiro passo<br /><em>para cuidar dos seus direitos.</em></h1><p>Após a confirmação do pagamento, você recebe um link por e-mail para concluir seu cadastro e acessar o painel.</p></div>
        {error && <p className="mp-error" role="alert">{error}</p>}
        {returning ? <div className="checkout-success" role="status"><h2>{status === "PAID" ? "Sua associação está ativa" : "Acompanhe a confirmação"}</h2><p>{statuses[status] || "Consultando seu pagamento…"}</p>{status !== "PAID" && <p>O retorno do PagBank não confirma o pagamento por si só. Você receberá um e-mail assim que a confirmação for concluída.</p>}<Link className="back-home" href="/acessar">Entrar ou reenviar acesso</Link>{["DECLINED", "CANCELED", "EXPIRED", "REVOKED"].includes(status) && <button className="checkout-submit" onClick={retry}>Tentar novamente</button>}</div>
          : <form className="pagbank-form" onSubmit={pay}>
            <h2>Adesão anual</h2><p>Informe seus dados e pague no ambiente seguro do PagBank. Use um e-mail ao qual você tenha acesso: ele será usado na sua conta Iustus.</p>
            <ol><li>Confirme o pagamento da adesão.</li><li>Conclua o cadastro pelo link recebido por e-mail.</li><li>Cadastre sua ocorrência para análise do advogado.</li></ol>
            <label className="checkout-acceptance"><input type="checkbox" required checked={accepted} onChange={e => setAccepted(e.target.checked)} />Entendi que cada ocorrência passa por análise e que a procuração específica será solicitada após o aceite do caso. A adesão é anual, sem renovação automática nesta contratação.</label>
            {plan?.sandbox && plan.available && <p role="note">Ambiente de teste: utilize somente dados de teste do PagBank.</p>}
            {plan && !plan.available && <p role="status">A adesão online está em preparação. Associados com acesso já ativado podem entrar normalmente.</p>}
            <button className="checkout-submit" disabled={busy || !checkoutReady || !accepted || !plan?.available}>{busy ? "Preparando pagamento…" : `Continuar no PagBank${plan ? " · 12x de " + money(plan.amount / 12) : ""}`}</button>
          </form>}
      </section>
      <aside className="order-summary" aria-label="Resumo da adesão"><div className="summary-top"><span>ASSOCIAÇÃO ANUAL</span><b>Acompanhamento online</b></div><h2>Iustus</h2><div className="summary-price"><small>Associação anual · 12x de</small><strong>{plan ? money(plan.amount / 12) : "Carregando…"}</strong><p>{plan ? `12 parcelas de ${money(plan.amount / 12)} no cartão. Total de ${money(plan.amount)}.` : "Carregando condições de pagamento…"}</p></div><ul><li>Cadastro de ocorrências durante a vigência</li><li>Análise individual por advogado</li><li>Procuração específica após o aceite de cada caso</li><li>Documentos, histórico e acompanhamento no painel</li><li>Avisos por e-mail sobre o atendimento</li></ul><p>Multas de trânsito e direito civil, exceto família e sucessões. O envio de uma ocorrência não garante seu aceite.</p></aside>
    </div>
  </main>;
}
