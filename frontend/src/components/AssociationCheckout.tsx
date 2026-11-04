"use client";

import Link from "next/link";
import Script from "next/script";
import { FormEvent, useEffect, useRef, useState } from "react";
import { isBillingPlan } from "../../../contracts/validation";
import { api, ApiError } from "@/lib/api/client";
import type { BillingPlan as Plan } from "../../../contracts/api";

type Customer = { name: string; email: string; cpf: string; phone: string };
type CardData = { token: string; payment_method_id: string; issuer_id: string | number; installments: number };
type Payment = { accepted: boolean; automaticRenewal: boolean; planVersion: string; policyVersion: string; customer: Customer; card: { token: string; paymentMethodId: string; issuerId: string; installments: number } };
type Controller = { unmount(): void | Promise<void> };
type MercadoPagoSDK = { bricks(): { create(name: string, element: string, settings: object): Promise<Controller> } };
declare global { interface Window { MercadoPago?: new (key: string, options: { locale: string }) => MercadoPagoSDK } }
const money = (cents: number) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const terminal = ["DECLINED", "CANCELED", "EXPIRED", "REVOKED"];
const statuses: Record<string, string> = {
  REVIEW: "Esta tentativa precisa de conferência pela associação. Entre em contato antes de pagar novamente.",
  CREATING: "Estamos conferindo sua tentativa. Aguarde antes de iniciar outro pagamento.",
  WAITING: "Pagamento enviado. Aguardando confirmação do Mercado Pago.",
  PAID: "Pagamento confirmado! Enviamos por e-mail as instruções de acesso. Você pode gerenciar a renovação automática em Minha conta.",
  DECLINED: "O cartão não foi aprovado. Confira os dados ou tente outro cartão.",
  CANCELED: "O pagamento foi cancelado.", EXPIRED: "O prazo deste pagamento terminou.",
  REVOKED: "O pagamento foi estornado ou contestado. Consulte sua conta.",
};
const digits = (value: string) => value.replace(/\D/g, "");
function validCpf(value: string) {
  return /^\d{11}$/.test(value) && new Set(value).size > 1 && [9, 10].every(size =>
    ((Array.from(value.slice(0, size)).reduce((sum, char, i) => sum + Number(char) * (size + 1 - i), 0) * 10 % 11) % 10) === Number(value[size]));
}

function CardPayment({ publicKey, plan, customer, onSubmit, onError }: {
  publicKey: string; plan: Plan; customer: Customer; onSubmit: (data: CardData) => Promise<void>; onError: (message: string) => void;
}) {
  const [sdkReady, setSdkReady] = useState(false);
  const [ready, setReady] = useState(false);
  const submit = useRef(onSubmit); submit.current = onSubmit;
  const error = useRef(onError); error.current = onError;
  useEffect(() => {
    if (!sdkReady || !window.MercadoPago) return;
    let active = true;
    let controller: Controller | undefined;
    const mp = new window.MercadoPago(publicKey, { locale: "pt-BR" });
    mp.bricks().create("cardPayment", "iustus-card-payment", {
      initialization: { amount: plan.amount / 100, payer: { email: customer.email } },
      customization: { visual: { style: { theme: "dark" } }, paymentMethods: { types: { included: ["credit_card"] }, minInstallments: plan.installments, maxInstallments: plan.installments } },
      callbacks: { onReady: () => { if (active) setReady(true); },
        onSubmit: (data: CardData) => submit.current(data),
        onError: () => { if (active) error.current("Não foi possível preparar o cartão. Confira os dados e tente novamente."); } },
    }).then(value => { controller = value; if (!active) void value.unmount(); })
      .catch(() => { if (active) error.current("Não foi possível carregar o pagamento seguro. Atualize a página."); });
    return () => { active = false; if (controller) void controller.unmount(); };
  }, [sdkReady, publicKey, plan.amount, plan.installments, customer.email]);
  return <>
    <Script src="https://sdk.mercadopago.com/js/v2" strategy="afterInteractive" onReady={() => setSdkReady(Boolean(window.MercadoPago))} onError={() => onError("Não foi possível carregar o Mercado Pago. Atualize a página.")} />
    {!ready && <p role="status">Preparando pagamento seguro…</p>}
    <div id="iustus-card-payment" />
  </>;
}

export default function AssociationCheckout() {
  const [plan, setPlan] = useState<Plan>();
  const [publicKey, setPublicKey] = useState("");
  const [customer, setCustomer] = useState<Customer>();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [checkoutReady, setCheckoutReady] = useState(false);
  const requestKey = useRef("");
  const payment = useRef<Payment | null>(null);
  const submitting = useRef(false);
  const amount = plan?.amount ?? 69990;
  const installments = plan?.installments ?? 10;

  useEffect(() => {
    let current = true;
    try {
      requestKey.current = sessionStorage.getItem("iustus-checkout-key") || crypto.randomUUID();
      sessionStorage.setItem("iustus-checkout-key", requestKey.current);
    } catch { requestKey.current = crypto.randomUUID(); }
    api<unknown>("billing/plan").then(async data => {
      if (!current) return;
      if (!isBillingPlan(data) || data.provider !== "mercadopago" || !data.automaticRenewal) throw new Error("INVALID_PLAN_RESPONSE");
      setPlan(data);
      if (data.available) {
        const key = await api<{ publicKey: string }>("billing/card-key");
        if (current) setPublicKey(key.publicKey);
      }
    }).catch(() => { if (current) setError("Não foi possível preparar o pagamento. Atualize a página para tentar novamente."); });
    api<{ status: string }>("billing/checkout").then(data => {
      if (current) { setStatus(data.status); setCheckoutReady(true); }
    }).catch(e => {
      if (!current) return;
      if (e instanceof ApiError && e.httpStatus === 404) setCheckoutReady(true);
      else setError("Não foi possível consultar uma tentativa anterior. Atualize a página antes de pagar.");
    });
    return () => { current = false; };
  }, []);

  useEffect(() => {
    if (!["CREATING", "WAITING"].includes(status)) return;
    let current = true, checking = false;
    const check = async () => {
      if (checking) return;
      checking = true;
      try {
        const result = await api<{ status: string }>("billing/checkout");
        if (current) { setStatus(result.status); if (result.status !== "CREATING") setError(""); }
      } catch { if (current) setError("A confirmação também será enviada por e-mail. Não inicie outro pagamento enquanto esta tentativa estiver em conferência."); }
      finally { checking = false; }
    };
    void check();
    const interval = setInterval(() => { if (!document.hidden) void check(); }, 10000);
    return () => { current = false; clearInterval(interval); };
  }, [status]);

  async function submitPayment() {
    if (!payment.current || submitting.current) return;
    submitting.current = true; setBusy(true); setError("");
    try {
      const result = await api<{ status: string }>("billing/checkout", payment.current, { idempotencyKey: requestKey.current });
      payment.current = null; setStatus(result.status);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível concluir o pagamento.");
      if (e instanceof ApiError && ["INVALID_INPUT", "VALIDATION_ERROR", "ACCEPTANCE_REQUIRED", "BUYER_REVIEW_REQUIRED", "IDEMPOTENCY_REQUIRED", "PLAN_CHANGED", "SUBSCRIPTION_EXISTS", "BILLING_UNAVAILABLE"].includes(e.code)) payment.current = null;
      else setStatus("CREATING");
    } finally { submitting.current = false; setBusy(false); }
  }

  function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !checkoutReady || !plan?.available || !accepted || !publicKey) return;
    const data = new FormData(event.currentTarget);
    const value = (name: string) => String(data.get(name) || "").trim();
    const buyer = { name: value("name"), email: value("email").toLowerCase(), cpf: digits(value("cpf")), phone: digits(value("phone")) };
    if (buyer.email !== value("emailConfirmation").toLowerCase()) { setError("Os e-mails devem ser iguais. O acesso será enviado para esse endereço."); return; }
    if (!validCpf(buyer.cpf)) { setError("Informe um CPF válido para o associado."); return; }
    setError(""); setCustomer(buyer);
  }

  async function pay(card: CardData) {
    if (!customer || !plan || !accepted || submitting.current) return;
    if (Number(card.installments) !== plan.installments) { setError("Este plano exige 10 parcelas sem juros. Confira se o cartão oferece essa condição."); return; }
    payment.current = { accepted: true, automaticRenewal: true, planVersion: plan.planVersion, policyVersion: plan.policyVersion, customer,
      card: { token: card.token, paymentMethodId: card.payment_method_id, issuerId: String(card.issuer_id), installments: Number(card.installments) } };
    await submitPayment();
  }

  function retry() {
    requestKey.current = crypto.randomUUID();
    try { sessionStorage.setItem("iustus-checkout-key", requestKey.current); } catch { /* Sessão identifica a tentativa no servidor. */ }
    payment.current = null; setStatus(""); setError(""); setAccepted(false); setCustomer(undefined);
  }

  return <section id="checkout" className="checkout-page" aria-labelledby="checkout-title">
    <div className="checkout-container checkout-layout">
      <section className="checkout-form-wrap">
        <div className="checkout-heading"><span className="checkout-kicker">IUSTUS · UM PROJETO AJA ANADECON</span><h2 id="checkout-title">Faça sua adesão.</h2><p>Cadastre-se e pague com cartão pelo Mercado Pago. Após a confirmação, enviaremos o acesso por e-mail.</p></div>
        {error && <p className="mp-error" role="alert">{error}</p>}
        {status ? <div className="checkout-success" role="status"><h2>{status === "PAID" ? "Sua associação está ativa" : "Seu pagamento"}</h2><p>{statuses[status] || "Consultando seu pagamento…"}</p><Link className="back-home" href="/acessar">Entrar ou reenviar acesso</Link>{terminal.includes(status) && <button className="checkout-submit" onClick={retry}>Tentar novamente</button>}{status === "CREATING" && payment.current && <button className="checkout-submit" disabled={busy} onClick={submitPayment}>Reenviar a mesma tentativa</button>}{status === "CREATING" && !payment.current && <p>Aguarde a conferência desta tentativa. Se necessário, entre em contato com a associação.</p>}</div>
        : customer && plan ? <div className="pagbank-form"><p>Associado: {customer.name} · {customer.email}</p><p>{installments}x de {money(amount / installments)}, total de {money(amount)} por ano. Renovação automática anual nas mesmas condições, até cancelar.</p><CardPayment publicKey={publicKey} plan={plan} customer={customer} onSubmit={pay} onError={setError} /><p className="form-hint">Dados do cartão protegidos pelo Mercado Pago. O Iustus recebe apenas o token e mantém referências ao cofre para as renovações autorizadas.</p></div>
        : <form className="pagbank-form" onSubmit={prepare}>
          <fieldset disabled={busy}><legend>Cadastro do associado</legend>
            <label>Nome completo<input name="name" autoComplete="name" required minLength={3} maxLength={120} /></label>
            <label>E-mail do associado<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
            <label>Confirme seu e-mail<input name="emailConfirmation" type="email" autoComplete="off" required maxLength={254} /></label>
            <div className="form-grid"><label>CPF do associado<input name="cpf" inputMode="numeric" autoComplete="off" placeholder="000.000.000-00" required maxLength={14} /></label><label>Celular com DDD<input name="phone" type="tel" autoComplete="tel-national" placeholder="11999999999" pattern="[0-9]{11}" required maxLength={11} /></label></div>
          </fieldset>
          <div className="checkout-total"><strong>{installments}x de {money(amount / installments)} sem juros</strong><span>Total anual: {money(amount)}</span></div>
          <label className="checkout-acceptance"><input type="checkbox" required checked={accepted} onChange={e => setAccepted(e.target.checked)} />Autorizo a compra anual de {money(amount)} em {installments} parcelas e sua renovação automática anual nas mesmas condições. Posso cancelar a próxima renovação em Minha conta antes da cobrança. Honorários, custas e despesas são contratados separadamente por caso.</label>
          <p className="form-hint">Cada ocorrência passa por análise; a procuração específica é solicitada após o aceite. Leia os <Link href="/termos">termos</Link> e a <Link href="/privacidade">política de privacidade</Link>.</p>
          {plan?.sandbox && plan.available && <p className="checkout-notice">Ambiente de teste: utilize somente cartões e contas de teste do Mercado Pago.</p>}
          {plan && !plan.available && <p className="checkout-notice" role="status">O pagamento online ainda não está disponível. Associados podem entrar normalmente.</p>}
          <button className="checkout-submit" disabled={busy || !checkoutReady || !accepted || !plan?.available || !publicKey}>Continuar para pagamento seguro</button>
        </form>}
      </section>
      <aside className="order-summary" aria-label="Resumo da adesão"><div className="summary-top"><span>ASSOCIAÇÃO ANUAL</span><b>Acompanhamento online</b></div><h2>Iustus</h2><div className="summary-price"><small>{installments} parcelas sem juros de</small><strong>{money(amount / installments)}</strong><p>Total: {money(amount)} por ano.</p></div><ul><li>Acesso aos recursos da plataforma</li><li>Cadastro e acompanhamento de ocorrências</li><li>Documentos e histórico no painel</li><li>Renovação automática anual em {installments} parcelas</li><li>Cancele a próxima renovação em Minha conta</li></ul><p className="summary-description">Honorários e despesas à parte. Multas de trânsito e direito civil, exceto família e sucessões. O envio não garante aceite do caso.</p></aside>
    </div>
  </section>;
}
