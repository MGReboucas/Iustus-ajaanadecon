import Link from 'next/link';
import Brand from '@/components/Brand';
import { sandboxCheckoutEnabled } from '@/lib/payments';
import CheckoutContent from './CheckoutContent';
import './checkout.css';

export const dynamic = 'force-dynamic';

export default function Checkout() {
  if (sandboxCheckoutEnabled()) return <CheckoutContent />;
  return <main className="checkout-page">
    <header className="checkout-header"><div className="checkout-container"><Link href="/" className="checkout-logo" aria-label="Voltar para o início da ÍUSTUS"><Brand decorative /></Link></div></header>
    <div className="checkout-container"><section className="checkout-form-wrap" style={{ margin: '48px auto', maxWidth: 640 }}>
      <div className="checkout-heading"><span className="checkout-kicker">ÍUSTUS</span><h1>Contratação em breve.</h1><p>Estamos preparando a contratação online. Nenhuma cobrança está disponível neste momento.</p><p>Você já pode acessar a área do cliente. Criar uma conta não ativa uma assinatura nem gera cobrança.</p></div>
      <Link href="/acessar" className="back-home">Entrar ou criar conta</Link>
    </section></div>
  </main>;
}
