"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import UnifiedCardForm, { type Buyer } from "./UnifiedCardForm";
import { useEffect, useRef, useState } from "react";
import { isBillingPlan } from "../../../contracts/validation";
import { api, ApiError } from "@/lib/api/client";
import type { BillingPlan as Plan } from "../../../contracts/api";

type Customer = { name: string; email: string; cpf: string; phone: string };
type CardData = { token: string; payment_method_id: string; issuer_id: string | number; installments: number };
type Payment = { accepted: boolean; automaticRenewal: boolean; planVersion: string; policyVersion: string; customer: Customer; card: { token: string; paymentMethodId: string; issuerId: string; installments: number } };
const money = (cents: number) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const terminal = ["DECLINED", "CANCELED", "EXPIRED", "REVOKED"];
const statuses: Record<string, string> = {
  REDIRECTING: "Pagamento enviado. Abrindo o acompanhamento da sua tentativa…",
  REVIEW_AMOUNT: "O valor ou as parcelas retornados pelo Mercado Pago divergem do plano contratado. A adesão está em conferência; não faça outro pagamento.",
  TEST_ARCHIVED: "Esta tentativa de teste foi encerrada na aplicação.",
  REVIEW: "Esta tentativa precisa de conferência pela associação. Entre em contato antes de pagar novamente.",
  CREATING: "Estamos conferindo sua tentativa. Aguarde antes de iniciar outro pagamento.",
  WAITING: "Pagamento enviado. Aguardando confirmação do Mercado Pago.",
  PAID: "Pagamento confirmado! As instruções de acesso serão enviadas por e-mail. Confira também a pasta de spam. Se não receber, use a opção de reenviar acesso abaixo. Sua adesão vale por um ano, sem renovação automática.",
  DECLINED: "O cartão não foi aprovado. Confira os dados ou tente outro cartão.",
  CANCELED: "O pagamento foi cancelado.", EXPIRED: "O prazo deste pagamento terminou.",
  REVOKED: "O pagamento foi estornado ou contestado. Consulte sua conta.",
};
export default function AssociationCheckout() {
  const router = useRouter();
  const pathname = usePathname();
  const [plan, setPlan] = useState<Plan>();
  const [publicKey, setPublicKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [checkoutReady, setCheckoutReady] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
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
      if (!isBillingPlan(data) || data.provider !== "mercadopago" || data.automaticRenewal !== false) throw new Error("INVALID_PLAN_RESPONSE");
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
      payment.current = null;
      if (pathname === "/checkout/resultado") setStatus(result.status);
      else { setStatus("REDIRECTING"); router.push("/checkout/resultado"); }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível concluir o pagamento.");
      if (e instanceof ApiError && ["INVALID_INPUT", "VALIDATION_ERROR", "ACCEPTANCE_REQUIRED", "BUYER_REVIEW_REQUIRED", "IDEMPOTENCY_REQUIRED", "PLAN_CHANGED", "SUBSCRIPTION_EXISTS", "BILLING_UNAVAILABLE"].includes(e.code)) payment.current = null;
      else setStatus("CREATING");
    } finally { submitting.current = false; setBusy(false); }
  }

  async function pay(card: CardData, customer: Buyer) {
    if (!plan?.available || !publicKey || !checkoutReady || status || submitting.current) return;
    if (!Number.isInteger(card.installments) || card.installments < 1 || card.installments > plan.installments) return;
    payment.current = { accepted: true, automaticRenewal: false, planVersion: plan.planVersion, policyVersion: plan.policyVersion, customer,
      card: { token: card.token, paymentMethodId: card.payment_method_id, issuerId: String(card.issuer_id), installments: card.installments } };
    await submitPayment();
  }

  function retry() {
    requestKey.current = crypto.randomUUID();
    try { sessionStorage.setItem("iustus-checkout-key", requestKey.current); } catch { /* Sessão identifica a tentativa no servidor. */ }
    payment.current = null; setStatus(""); setError("");
  }

  async function resetTest() {
    if (busy || !plan?.sandbox) return;
    setBusy(true); setError("");
    try {
      await api("billing/checkout/reset-test", { confirm: true });
      retry(); setConfirmReset(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível encerrar o teste.");
    } finally { setBusy(false); }
  }

  return <section id="checkout" className="checkout-page" aria-labelledby="checkout-title">
    <div className="checkout-container checkout-layout">
      <section className="checkout-form-wrap">
        <div className="checkout-heading"><span className="checkout-kicker">IUSTUS · UM PROJETO AJA ANADECON</span><h2 id="checkout-title">Faça sua adesão.</h2><p>Cadastre-se e pague com cartão pelo Mercado Pago. Após a confirmação, enviaremos o acesso por e-mail.</p></div>
        {error && <p className="mp-error" role="alert">{error}</p>}
        {status && plan?.sandbox && !["PAID", "REVOKED"].includes(status) && <div className="checkout-notice">
          <strong>Ambiente de teste</strong>
          <p>A tentativa anterior está salva nesta sessão. Você pode arquivá-la e iniciar um novo teste. O histórico será preservado; esta ação não cancela nem estorna pedidos no Mercado Pago.</p>
          {confirmReset ? <>
            <p>Encerrar esta tentativa de teste e abrir um novo formulário?</p>
            <button type="button" className="checkout-submit" disabled={busy} onClick={resetTest}>{busy ? "Encerrando teste…" : "Confirmar novo teste"}</button>
            <button type="button" className="checkout-secondary" disabled={busy} onClick={() => setConfirmReset(false)}>Voltar</button>
          </> : <button type="button" className="checkout-submit" disabled={busy} onClick={() => setConfirmReset(true)}>Encerrar tentativa e iniciar novo teste</button>}
        </div>}
        {status ? <div className="checkout-success" role="status"><h2>{status === "PAID" ? "Sua associação está ativa" : "Seu pagamento"}</h2><p>{statuses[status] || "Consultando seu pagamento…"}</p><Link className="back-home" href="/acessar">Entrar ou reenviar acesso</Link>{terminal.includes(status) && <button className="checkout-submit" onClick={retry}>Tentar novamente</button>}{status === "CREATING" && payment.current && <button className="checkout-submit" disabled={busy} onClick={submitPayment}>Reenviar a mesma tentativa</button>}{status === "CREATING" && !payment.current && <p>Aguarde a conferência desta tentativa. Se necessário, entre em contato com a associação.</p>}</div>
        : <>
          {plan && !plan.available && <p className="checkout-notice" role="status">Pagamento indisponível no momento. Você pode preencher seus dados enquanto isso.</p>}
          <UnifiedCardForm publicKey={publicKey} amount={amount} maxInstallments={installments} busy={busy} enabled={checkoutReady && !!plan?.available && !!publicKey} sandbox={plan?.sandbox ?? false} onPay={pay} onError={setError} />
        </>}
      </section>
      <aside className="order-summary" aria-label="Resumo da adesão"><div className="summary-top"><span>ASSOCIAÇÃO ANUAL</span><b>Acompanhamento online</b></div><h2>Iustus</h2><div className="summary-price"><small>Associação anual</small><strong>{money(amount)}</strong><p>Escolha de 1 a {installments} parcelas, conforme as condições sem juros do cartão.</p></div><ul><li>Acesso aos recursos da plataforma</li><li>Cadastro e acompanhamento de ocorrências</li><li>Documentos e histórico no painel</li><li>Vigência de um ano</li><li>Renovação manual, sem cobranças automáticas</li></ul><p className="summary-description">Honorários e despesas à parte. Multas de trânsito e direito civil, exceto família e sucessões. O envio não garante aceite do caso.</p></aside>
    </div>
  </section>;
}
