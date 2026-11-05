"use client";

import Script from "next/script";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

export type Buyer = { name: string; email: string; cpf: string; phone: string };
export type Card = { token: string; payment_method_id: string; issuer_id: string; installments: number };
type Cost = { installments: number; installment_amount: number; total_amount: number };
type CardForm = { unmount(): void; getCardFormData(): { token: string; paymentMethodId: string; issuerId: string; installments: string } };
type SDK = { cardForm(options: object): CardForm };
const money = (value: number) => value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const cents = (value: number) => Math.round(value * 100);
const digits = (value: string) => value.replace(/\D/g, "");
function validCpf(value: string) {
  return /^\d{11}$/.test(value) && new Set(value).size > 1 && [9, 10].every(size =>
    ((Array.from(value.slice(0, size)).reduce((sum, char, i) => sum + Number(char) * (size + 1 - i), 0) * 10 % 11) % 10) === Number(value[size]));
}

export default function UnifiedCardForm({ publicKey, amount, maxInstallments, busy, enabled, sandbox, onPay, onError }: {
  publicKey: string; amount: number; maxInstallments: number; busy: boolean; enabled: boolean; sandbox: boolean;
  onPay: (card: Card, buyer: Buyer) => Promise<void>; onError: (message: string) => void;
}) {
  const form = useRef<HTMLFormElement>(null);
  const [sdkReady, setSdkReady] = useState(false);
  const [ready, setReady] = useState(false);
  const [quote, setQuote] = useState<Cost>();
  const [quoted, setQuoted] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const costs = useRef<Cost[]>([]);
  const selected = useRef<Cost | undefined>(undefined);
  const callbacks = useRef({ onPay, onError, enabled, busy, accepted });
  callbacks.current = { onPay, onError, enabled, busy, accepted };

  useEffect(() => {
    if (!sdkReady || !publicKey) return;
    let active = true;
    const Constructor = (window as unknown as { MercadoPago: new (key: string, options: object) => SDK }).MercadoPago;
    const select = document.getElementById("iustus-installments") as HTMLSelectElement;
    const sync = () => {
      if (!active) return;
      // Only provider quotes with no buyer surcharge can be offered by this plan.
      for (const option of Array.from(select.options)) {
        const cost = costs.current.find(item => Number(item.installments) === Number(option.value));
        const allowed = cost && Number.isInteger(Number(cost.installments)) && Number(cost.installments) >= 1
          && Number(cost.installments) <= maxInstallments && cents(Number(cost.total_amount)) === amount;
        option.disabled = !allowed;
        option.hidden = !allowed;
      }
      if (select.selectedOptions[0]?.disabled) select.value = "";
      const value = costs.current.find(item => Number(item.installments) === Number(select.value));
      selected.current = value && cents(Number(value.total_amount)) === amount ? value : undefined;
      setQuote(selected.current);
    };
    const observer = new MutationObserver(sync);
    observer.observe(select, { childList: true });
    select.addEventListener("change", sync);
    const secureStyle = { color: "#f2f5f8", fontSize: "16px", fontFamily: "Arial" };
    const instance = new Constructor(publicKey, { locale: "pt-BR" }).cardForm({
      amount: (amount / 100).toFixed(2), iframe: true,
      form: {
        id: "iustus-payment-form",
        cardNumber: { id: "iustus-card-number", placeholder: "Número do cartão", style: secureStyle },
        expirationDate: { id: "iustus-card-expiration", placeholder: "MM/AA", style: secureStyle },
        securityCode: { id: "iustus-card-cvv", placeholder: "CVV", style: secureStyle },
        cardholderName: { id: "iustus-holder" }, cardholderEmail: { id: "iustus-email" },
        issuer: { id: "iustus-issuer" }, installments: { id: "iustus-installments" },
        identificationType: { id: "iustus-document-type" }, identificationNumber: { id: "iustus-document" },
      },
      callbacks: {
        onFormMounted: (error: unknown) => { if (active && error) callbacks.current.onError("Não foi possível carregar os campos seguros do cartão."); },
        onReady: () => { if (active) setReady(true); },
        onBinChange: () => { costs.current = []; selected.current = undefined; if (active) { setQuote(undefined); setQuoted(false); } },
        onInstallmentsReceived: (error: unknown, data: { payer_costs?: Cost[] } | { payer_costs?: Cost[] }[]) => {
          if (!active) return;
          costs.current = error ? [] : (Array.isArray(data) ? data[0]?.payer_costs : data?.payer_costs) || [];
          setQuoted(true); sync();
        },
        onSubmit: async (event: Event) => {
          event.preventDefault();
          const state = callbacks.current;
          if (!active || !state.enabled || state.busy || !state.accepted || !form.current?.reportValidity()) return;
          const data = new FormData(form.current);
          const text = (name: string) => String(data.get(name) || "").trim();
          const buyer = { name: text("name"), email: text("email").toLowerCase(), cpf: digits(text("cpf")), phone: digits(text("phone")) };
          if (buyer.email !== text("emailConfirmation").toLowerCase()) { state.onError("Os e-mails devem ser iguais."); return; }
          if (!validCpf(buyer.cpf)) { state.onError("Informe um CPF válido para o associado."); return; }
          const card = instance.getCardFormData();
          const cost = selected.current;
          if (!cost || Number(card.installments) !== Number(cost.installments) || cents(Number(cost.total_amount)) !== amount) {
            state.onError("Selecione uma condição sem juros confirmada pelo Mercado Pago antes de pagar."); return;
          }
          await state.onPay({ token: card.token, payment_method_id: card.paymentMethodId, issuer_id: card.issuerId, installments: Number(card.installments) }, buyer);
        },
        onError: () => { if (active) callbacks.current.onError("Confira os dados do cartão e a condição de parcelamento."); },
      },
    });
    return () => { active = false; observer.disconnect(); select.removeEventListener("change", sync); instance.unmount(); };
  }, [sdkReady, publicKey, amount, maxInstallments]);

  return <form id="iustus-payment-form" ref={form} className="association-form unified-checkout" onSubmit={e => e.preventDefault()}>
    <Script src="https://sdk.mercadopago.com/js/v2" strategy="afterInteractive" onReady={() => setSdkReady(true)} onError={() => onError("Não foi possível carregar o Mercado Pago. Atualize a página.")} />
    <fieldset disabled={busy}><legend><span>01</span> Dados do associado</legend>
      <label>Nome completo<input name="name" autoComplete="name" required minLength={3} maxLength={120} /></label>
      <div className="form-grid"><label>E-mail do associado<input id="iustus-email" name="email" type="email" autoComplete="email" required maxLength={254} /></label>
      <label>Confirme seu e-mail<input name="emailConfirmation" type="email" autoComplete="off" required maxLength={254} /></label></div>
      <div className="form-grid"><label>CPF do associado<input name="cpf" inputMode="numeric" placeholder="000.000.000-00" required maxLength={14} /></label>
      <label>Celular com DDD<input name="phone" type="tel" autoComplete="tel-national" placeholder="11999999999" pattern="[1-9][0-9]9[0-9]{8}" required maxLength={11} /></label></div>
    </fieldset>
    <fieldset disabled={busy}><legend><span>02</span> Forma de pagamento</legend>
      <label>Como deseja pagar?<select name="paymentMethod" defaultValue="credit_card">
        <option value="credit_card">Cartão de crédito</option>
        <option value="pix" disabled>Pix — indisponível no momento</option>
      </select></label>
    </fieldset>
    <fieldset disabled={busy}><legend><span>03</span> Cartão de crédito</legend>
      <label>Número do cartão<div id="iustus-card-number" className="secure-card-field" /></label>
      <div className="form-grid"><label>Validade<div id="iustus-card-expiration" className="secure-card-field" /></label><label>Código de segurança<div id="iustus-card-cvv" className="secure-card-field" /></label></div>
      <label>Nome impresso no cartão<input id="iustus-holder" autoComplete="cc-name" required /></label>
      <div className="form-grid"><label>Tipo de documento do titular<select id="iustus-document-type" required /></label><label>Documento do titular<input id="iustus-document" inputMode="numeric" required /></label></div>
      <label>Banco emissor<select id="iustus-issuer" required /></label>
      <p className="form-hint">Número, validade e CVV são preenchidos nos campos protegidos do Mercado Pago.</p>
      <p className="form-hint">Informe os dados do cartão para consultar as parcelas disponíveis. Exibimos somente condições que mantêm o total de {money(amount / 100)}, sem juros.</p>
      <label>Quantidade de parcelas<select id="iustus-installments" required defaultValue=""><option value="" disabled>Preencha o cartão para consultar</option></select></label>
      <div className="checkout-total" aria-live="polite"><strong>{quote ? `${quote.installments}x de ${money(Number(quote.installment_amount))} sem juros` : `Total da adesão: ${money(amount / 100)}`}</strong>
        <span>{quote ? `Total a pagar: ${money(Number(quote.total_amount))}` : "Selecione uma condição para confirmar o pagamento."}</span></div>
      {quoted && !costs.current.some(cost => Number(cost.installments) <= maxInstallments && cents(Number(cost.total_amount)) === amount) && <p className="mp-error">Este cartão não retornou uma condição sem juros. Nenhum pagamento foi enviado. Confira o parcelamento da conta Mercado Pago ou utilize outro cartão.</p>}
    </fieldset>
    <label className="checkout-acceptance"><input type="checkbox" required checked={accepted} onChange={e => setAccepted(e.target.checked)} /><span>Autorizo a compra anual de {money(amount / 100)}, nas parcelas selecionadas, sem renovação automática. Li os <Link href="/termos">termos</Link> e a <Link href="/privacidade">política de privacidade</Link>.</span></label>
    {sandbox && <p className="checkout-notice">Ambiente de teste. Utilize somente cartões e contas de teste.</p>}
    {!ready && <p role="status">Preparando campos seguros…</p>}
    <button className="checkout-submit" type="submit" disabled={busy || !ready || !enabled || !accepted || !quote}>{busy ? "Enviando pagamento…" : `Pagar ${money(amount / 100)}`}</button>
  </form>;
}
