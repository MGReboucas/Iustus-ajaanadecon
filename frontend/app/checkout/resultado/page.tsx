import Link from "next/link";
import AssociationCheckout from "@/components/AssociationCheckout";
import "../checkout.css";
import "../association.css";

export const metadata = { title: "Resultado do pagamento", robots: { index: false, follow: false } };
export default function CheckoutResult() {
  return <main className="checkout-result-page"><div className="checkout-container"><Link className="back-home" href="/">← Voltar para Iustus</Link></div><AssociationCheckout /></main>;
}
