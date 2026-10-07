"use client";

import Link from "next/link";
import Script from "next/script";
import { FormEvent, useEffect, useRef, useState } from "react";
import Brand from "./Brand";
import { api, ApiError } from "@/lib/api/client";

import type { BillingPlan as Plan } from "../../../contracts/api";
type Payment = { accepted: boolean; customer: { name: string; email: string; cpf: string; phone: string }; card: { encrypted: string; holderName: string; holderCpf: string } };
type CardSDK = { encryptCard(data: { publicKey: string; holder: string; number: string; expMonth: string; expYear: string; securityCode: string }): { encryptedCard?: string; hasErrors: boolean; errors?: { code: string }[] } };
declare global { interface Window { PagSeguro?: CardSDK } }
const money = (value: number) => (value / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const terminal = ["DECLINED", "CANCELED", "EXPIRED", "REVOKED"];
const statuses: Record<string, string> = {
  CREATING: "Estamos conferindo sua tentativa. Aguarde a confirmação antes de iniciar outro pagamento.",
  WAITING: "Pagamento enviado. Aguardando a confirmação da operadora do cartão.",
  PAID: "Pagamento confirmado! Enviamos ao e-mail do associado as instruções para acessar o painel. Se você já possui conta, pode entrar normalmente.",
  DECLINED: "O cartão não foi aprovado. Confira os dados ou tente outro cartão.",
  CANCELED: "O pagamento foi cancelado. Você pode tentar novamente.",
  EXPIRED: "O prazo deste pagamento terminou. Você pode tentar novamente.",
  REVOKED: "O pagamento foi estornado ou cancelado. Consulte sua conta para acompanhar a associação.",
};
const cardErrors: Record<string, string> = {
  INVALID_NUMBER: "Confira o número do cartão.", INVALID_SECURITY_CODE: "Confira o código de segurança do cartão.",
  INVALID_EXPIRATION_MONTH: "Confira o mês de validade.", INVALID_EXPIRATION_YEAR: "Confira o ano de validade.",
  INVALID_HOLDER: "Informe o nome completo do titular do cartão.", INVALID_PUBLIC_KEY: "Não foi possível preparar o cartão. Atualize a página.",
};
const digits = (value: string) => value.replace(/\D/g, "");
function validCpf(value: string) {
  if (!/^\d{11}$/.test(value) || new Set(value).size === 1) return false;
  return [9, 10].every(size => ((Array.from(value.slice(0, size)).reduce((sum, char, i) => sum + Number(char) * (size + 1 - i), 0) * 10 % 11) % 10) === Number(value[size]));
}

export default function AssociationCheckout() {
  const [plan, setPlan] = useState<Plan>();
  const [publicKey, setPublicKey] = useState("");
  const [sdkReady, setSdkReady] = useState(false);
  const [sameHolder, setSameHolder] = useState(true);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [checkoutReady, setCheckoutReady] = useState(false);
  const requestKey = useRef("");
  const payment = useRef<Payment | null>(null);
  const submitting = useRef(false);
  // A oferta aparece no HTML inicial, mesmo antes de a API responder.
  const amount = plan?.amount ?? 69990;
  const installments = plan?.installments ?? 10;

  useEffect(() => {
    let current = true;
    try {
      requestKey.current = sessionStorage.getItem("iustus-checkout-key") || crypto.randomUUID();
      sessionStorage.setItem("iustus-checkout-key", requestKey.current);
    } catch { requestKey.current = crypto.randomUUID(); }
    api<Plan>("billing/plan").then(async data => {
      if (!current) return;
      setPlan(data);
      if (data.available) {
        const key = await api<{ publicKey: string }>("billing/card-key");
        if (current) setPublicKey(key.publicKey);
      }
    }).catch(() => { if (current) setError("Não foi possível preparar o pagamento. Seus dados ainda não foram enviados. Atualize a página para tentar novamente."); });
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
    let current = true;
    let checking = false;
    const check = async () => {
      if (checking) return;
      checking = true;
      try {
        const result = await api<{ status: string }>("billing/checkout");
        if (current) { setStatus(result.status); if (result.status !== "CREATING") setError(""); }
      } catch { if (current) setError("A consulta está indisponível. A confirmação também será enviada por e-mail. Não inicie outro pagamento enquanto esta tentativa estiver em conferência."); }
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
      // Somente erros anteriores à cobrança permitem alterar os dados.
      if (e instanceof ApiError && ["INVALID_INPUT", "VALIDATION_ERROR", "ACCEPTANCE_REQUIRED", "BUYER_REVIEW_REQUIRED", "IDEMPOTENCY_REQUIRED"].includes(e.code)) {
        payment.current = null;
      } else setStatus("CREATING");
    } finally { submitting.current = false; setBusy(false); }
  }

  async function pay(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || !checkoutReady || !plan?.available || !publicKey || !window.PagSeguro) return;
    setError("");
    const form = event.currentTarget;
    const data = new FormData(form);
    const value = (name: string) => String(data.get(name) || "").trim();
    const customer = { name: value("name"), email: value("email").toLowerCase(), cpf: digits(value("cpf")), phone: digits(value("phone")) };
    if (customer.email !== value("emailConfirmation").toLowerCase()) { setError("Os e-mails devem ser iguais. O acesso será enviado para esse endereço."); return; }
    if (!validCpf(customer.cpf)) { setError("Informe um CPF válido para o associado."); return; }
    const holderName = sameHolder ? customer.name : value("holderName");
    const holderCpf = sameHolder ? customer.cpf : digits(value("holderCpf"));
    if (!validCpf(holderCpf)) { setError("Informe um CPF válido para o titular do cartão."); return; }
    const expiry = digits(value("expiry"));
    const month = Number(expiry.slice(0, 2));
    const year = Number("20" + expiry.slice(2));
    if (expiry.length !== 4 || month < 1 || month > 12 || new Date(year, month, 1) <= new Date()) { setError("Informe uma validade futura no formato MM/AA."); return; }
    try {
      const encrypted = window.PagSeguro.encryptCard({ publicKey, holder: holderName, number: digits(value("cardNumber")), expMonth: String(month).padStart(2, "0"), expYear: String(year), securityCode: value("cvv") });
      if (encrypted.hasErrors || !encrypted.encryptedCard) { setError(cardErrors[encrypted.errors?.[0]?.code || ""] || "Confira os dados do cartão e tente novamente."); return; }
      payment.current = { accepted, customer, card: { encrypted: encrypted.encryptedCard, holderName, holderCpf } };
      // Dados abertos do cartão não entram na API, armazenamento ou logs do site.
      for (const name of ["cardNumber", "expiry", "cvv"]) (form.elements.namedItem(name) as HTMLInputElement).value = "";
      await submitPayment();
    } catch { setError("Não foi possível proteger os dados do cartão. Atualize a página e tente novamente."); }
  }

  function retry() {
    requestKey.current = crypto.randomUUID();
    try { sessionStorage.setItem("iustus-checkout-key", requestKey.current); } catch { /* A sessão do servidor também identifica a tentativa. */ }
    payment.current = null; setStatus(""); setError(""); setAccepted(false);
  }

  return <main className="checkout-page">
    <Script src="https://assets.pagseguro.com.br/checkout-sdk-js/rc/dist/browser/pagseguro.min.js" strategy="afterInteractive" onReady={() => setSdkReady(Boolean(window.PagSeguro))} onError={() => setError("Não foi possível carregar o pagamento seguro. Atualize a página para tentar novamente.")} />
    <header className="checkout-header"><div className="checkout-container"><Link href="/" className="checkout-logo" aria-label="Voltar para a Iustus"><Brand decorative /></Link><Link href="/acessar" className="back-link">Já sou associado</Link></div></header>
    <div className="checkout-container checkout-layout">
      <section className="checkout-form-wrap" aria-labelledby="checkout-title">
        <div className="checkout-heading"><span className="checkout-kicker">IUSTUS · UM PROJETO AJA ANADECON</span><h1 id="checkout-title">Faça sua adesão.</h1><p>Preencha seu cadastro e pague aqui com cartão. Seu e-mail e CPF identificam sua associação. Após a confirmação, enviaremos o acesso ao painel por e-mail.</p></div>
        {error && <p className="mp-error" role="alert">{error}</p>}
        {status ? <div className="checkout-success" role="status"><h2>{status === "PAID" ? "Sua associação está ativa" : "Seu pagamento"}</h2><p>{statuses[status] || "Consultando seu pagamento…"}</p><Link className="back-home" href="/acessar">Entrar ou reenviar acesso</Link>{terminal.includes(status) && <button className="checkout-submit" onClick={retry}>Tentar novamente</button>}{status === "CREATING" && payment.current && <button className="checkout-submit" disabled={busy} onClick={submitPayment}>{busy ? "Conferindo…" : "Reenviar a mesma tentativa"}</button>}{status === "CREATING" && !payment.current && <p>Se a confirmação não chegar, entre em contato com a associação para conferir esta tentativa.</p>}</div>
          : <form className="pagbank-form" onSubmit={pay}>
            <fieldset disabled={busy}><legend>1. Cadastro do associado</legend>
              <label>Nome completo<input name="name" autoComplete="section-member name" required minLength={3} maxLength={120} /></label>
              <label>E-mail do associado<input name="email" type="email" autoComplete="section-member email" required maxLength={254} /></label>
              <label>Confirme seu e-mail<input name="emailConfirmation" type="email" autoComplete="off" required maxLength={254} /></label>
              <div className="form-grid"><label>CPF do associado<input name="cpf" inputMode="numeric" autoComplete="off" placeholder="000.000.000-00" required maxLength={14} /></label><label>Celular com DDD<input name="phone" type="tel" autoComplete="section-member tel-national" placeholder="11999999999" pattern="[0-9]{11}" title="Informe os 11 números do celular, incluindo o DDD." required maxLength={11} /></label></div>
              <p className="form-hint">Use seu próprio e-mail e CPF, mesmo que outra pessoa pague com o cartão dela.</p>
            </fieldset>
            <fieldset disabled={busy}><legend>2. Pagamento com cartão de crédito</legend>
              <div className="checkout-total"><strong>{installments}x de {money(amount / installments)} sem juros</strong><span>Total da adesão anual: {money(amount)}</span></div>
              <label className="checkout-acceptance"><input type="checkbox" checked={sameHolder} onChange={e => setSameHolder(e.target.checked)} />O cartão está no nome do associado.</label>
              {!sameHolder && <><label>Nome do titular do cartão<input name="holderName" autoComplete="cc-name" required minLength={3} maxLength={120} /></label><label>CPF do titular do cartão<input name="holderCpf" inputMode="numeric" autoComplete="off" required maxLength={14} /></label></>}
              <label>Número do cartão<input name="cardNumber" inputMode="numeric" autoComplete="cc-number" placeholder="0000 0000 0000 0000" required minLength={13} maxLength={23} /></label>
              <div className="form-grid"><label>Validade (MM/AA)<input name="expiry" inputMode="numeric" autoComplete="cc-exp" placeholder="MM/AA" required pattern="[0-9]{2}/?[0-9]{2}" maxLength={5} /></label><label>Código de segurança (CVV)<input name="cvv" type="password" inputMode="numeric" autoComplete="cc-csc" placeholder="3 ou 4 dígitos" required pattern="[0-9]{3,4}" maxLength={4} /></label></div>
              <p className="form-hint">Pagamento processado pelo PagBank. Os dados do cartão são criptografados antes do envio.</p>
            </fieldset>
            <label className="checkout-acceptance"><input type="checkbox" required disabled={busy} checked={accepted} onChange={e => setAccepted(e.target.checked)} />Entendi que cada ocorrência passa por análise e que a procuração específica será solicitada após o aceite do caso. A adesão é anual, sem renovação automática nesta contratação.</label>
            {plan?.sandbox && plan.available && <p className="checkout-notice" role="note">Ambiente de teste: utilize somente dados de teste do PagBank.</p>}
            {plan && !plan.available && <p className="checkout-notice" role="status">O pagamento online ainda não está disponível. Associados com acesso ativado podem entrar normalmente.</p>}
            <button className="checkout-submit" disabled={busy || !checkoutReady || !accepted || !plan?.available || !sdkReady || !publicKey}>{busy ? "Processando pagamento…" : `Pagar · ${installments}x de ` + money(amount / installments)}</button>
            {(!checkoutReady || (plan?.available && (!publicKey || !sdkReady))) && <p className="form-hint">{error ? "Atualize a página para carregar o pagamento." : "Preparando pagamento seguro…"}</p>}
          </form>}
      </section>
      <aside className="order-summary" aria-label="Resumo da adesão"><div className="summary-top"><span>ASSOCIAÇÃO ANUAL</span><b>Acompanhamento online</b></div><h2>Iustus</h2><div className="summary-price"><small>{installments} parcelas sem juros de</small><strong>{money(amount / installments)}</strong><p>Total: {money(amount)} no cartão de crédito.</p></div><ul><li>Cadastro de ocorrências durante a vigência</li><li>Análise individual por advogado</li><li>Procuração específica após o aceite de cada caso</li><li>Documentos, histórico e acompanhamento no painel</li><li>Avisos por e-mail sobre o atendimento</li></ul><p className="summary-description">Multas de trânsito e direito civil, exceto família e sucessões. O envio de uma ocorrência não garante seu aceite.</p><div className="summary-security"><p><b>Um projeto AJA ANADECON</b>Associação vinculada ao e-mail e CPF informados no cadastro.</p></div></aside>
    </div>
  </main>;
}
