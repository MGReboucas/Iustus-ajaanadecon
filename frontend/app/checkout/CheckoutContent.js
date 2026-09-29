'use client';

import Link from 'next/link';
import Brand from '@/components/Brand';
import { useState } from 'react';
import './checkout.css';
import './pagbank.css';
import PagBankTransparentForm from './PagBankTransparentForm';

const Check = () => <span className="check" aria-hidden="true">✓</span>;

export default function CheckoutContent() {
  const [payment, setPayment] = useState(null);
  const [quote, setQuote] = useState(null);

  return (
    <main className="checkout-page">
      <header className="checkout-header"><div className="checkout-container"><Link href="/" className="checkout-logo" aria-label="Voltar para o início da ÍUSTUS"><Brand decorative /></Link><Link href="/" className="back-link">← Voltar para o site</Link></div></header>

      <div className="checkout-container checkout-layout">
        <section className="checkout-form-wrap" aria-labelledby="checkout-title">
          <div className="checkout-progress" aria-label="Etapa 1 de 2"><span className="progress-current">1</span><i></i><span>2</span><small>Dados e pagamento</small></div>
          {!payment ? <><div className="checkout-heading"><span className="checkout-kicker">ASSINATURA ANUAL</span><h1 id="checkout-title">Comece sua proteção<br /><em>com a ÍUSTUS.</em></h1><p>Preencha os dados do cartão para visualizar as parcelas e juros configurados pelo PagBank.</p></div><PagBankTransparentForm onApproved={setPayment} onInstallmentChange={setQuote} /></> : <div className="checkout-success" role="status"><span><Check /></span><h1>Assinatura aprovada.</h1><p>Seu pagamento em {payment.installments}x foi aprovado. Seu acesso à ÍUSTUS será liberado conforme a confirmação da assinatura.</p><Link href="/" className="back-home">Voltar para a ÍUSTUS</Link></div>}
        </section>
        <aside className="order-summary" aria-label="Resumo do pedido"><div className="summary-top"><span>SEU PLANO</span><b>Uso ilimitado</b></div><h2>ÍUSTUS Anual</h2><p className="summary-description">A plataforma para acompanhar seus casos sempre que você precisar.</p><div className="machine-fee"><small>Juros da maquininha</small><b>{quote ? (quote.interestFree ? 'Sem juros' : `R$ ${(quote.totalAmount - 547).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`) : 'Informe o cartão'}</b></div><div className="summary-price"><small>{quote ? `Total em ${quote.installments}x` : 'Valor base anual'}</small><strong>R$ {(quote ? quote.totalAmount : 547).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong><p>{quote ? `${quote.installments}x de R$ ${quote.installmentAmount.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Parcelas e juros serão exibidos após informar o cartão.'}</p></div><ul><li><Check /> Envie quantos casos precisar</li><li><Check /> Anexe documentos e procuração</li><li><Check /> Acompanhe tudo pelo dashboard</li><li><Check /> Receba sua defesa na plataforma</li></ul><div className="summary-security"><span>⌁</span><p><b>Dados do cartão protegidos</b>Cartão tokenizado pelo PagBank.</p></div></aside>
      </div>
      <section className="checkout-assurance"><div className="checkout-container"><div><Check /><span><b>Assinatura anual</b>Um plano claro, sem contratação por caso.</span></div><div><Check /><span><b>Uso ilimitado</b>Envie casos durante toda a vigência.</span></div><div><Check /><span><b>Jornada digital</b>Do envio à defesa, no mesmo painel.</span></div></div></section>
    </main>
  );
}
