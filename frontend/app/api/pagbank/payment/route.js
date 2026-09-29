import { randomUUID } from 'crypto';
import { sandboxCheckoutEnabled } from '@/lib/payments';

export async function POST(request) {
  if (!sandboxCheckoutEnabled()) return Response.json({ message: 'A contratação online ainda não está disponível.' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  const email = process.env.PAGBANK_EMAIL;
  const token = process.env.PAGBANK_TOKEN;
  const sandbox = process.env.NEXT_PUBLIC_PAGBANK_SANDBOX !== 'false';
  if (!email || !token) return Response.json({ message: 'Configure as credenciais do PagBank no servidor.' }, { status: 503 });
  const { cardToken, senderHash, installment, form } = await request.json();
  if (!cardToken || !senderHash || !installment || !form?.email || !form?.cpf) return Response.json({ message: 'Dados de pagamento incompletos.' }, { status: 400 });
  const digits = (value) => String(value || '').replace(/\D/g, '');
  const [areaCode, phone] = [digits(form.phone).slice(0, 2), digits(form.phone).slice(2)];
  const body = new URLSearchParams({ paymentMode: 'default', paymentMethod: 'creditCard', receiverEmail: email, currency: 'BRL', itemId1: 'iustus-anual', itemDescription1: 'Assinatura anual IUSTUS', itemAmount1: '547.00', itemQuantity1: '1', reference: `iustus-${randomUUID()}`, senderName: form.name, senderCPF: digits(form.cpf), senderAreaCode: areaCode, senderPhone: phone, senderEmail: form.email, senderHash, shippingAddressRequired: 'false', creditCardToken: cardToken, installmentQuantity: String(installment.quantity), installmentValue: Number(installment.installmentAmount).toFixed(2), creditCardHolderName: form.name, creditCardHolderCPF: digits(form.cpf), creditCardHolderBirthDate: form.birthDate, creditCardHolderAreaCode: areaCode, creditCardHolderPhone: phone, billingAddressStreet: form.street, billingAddressNumber: form.number, billingAddressComplement: form.complement || '', billingAddressDistrict: form.district, billingAddressPostalCode: digits(form.postalCode), billingAddressCity: form.city, billingAddressState: form.state, billingAddressCountry: 'BRA' });
  const baseUrl = sandbox ? 'https://ws.sandbox.pagseguro.uol.com.br' : 'https://ws.pagseguro.uol.com.br';
  const response = await fetch(`${baseUrl}/v2/transactions?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', Accept: 'application/xml' }, body });
  const xml = await response.text();
  const code = xml.match(/<code>([^<]+)<\/code>/)?.[1];
  if (!response.ok || !code) return Response.json({ message: 'Pagamento não aprovado pelo PagBank.' }, { status: 502 });
  return Response.json({ code });
}
