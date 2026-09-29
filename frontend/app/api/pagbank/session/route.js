import { sandboxCheckoutEnabled } from '@/lib/payments';

export async function GET() {
  if (!sandboxCheckoutEnabled()) return Response.json({ message: 'A contratação online ainda não está disponível.' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  const email = process.env.PAGBANK_EMAIL;
  const token = process.env.PAGBANK_TOKEN;
  const sandbox = process.env.NEXT_PUBLIC_PAGBANK_SANDBOX !== 'false';
  if (!email || !token) return Response.json({ message: 'Configure PAGBANK_EMAIL e PAGBANK_TOKEN no servidor.' }, { status: 503 });
  const baseUrl = sandbox ? 'https://ws.sandbox.pagseguro.uol.com.br' : 'https://ws.pagseguro.uol.com.br';
  const response = await fetch(`${baseUrl}/v2/sessions?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`, { method: 'POST' });
  const xml = await response.text();
  const id = xml.match(/<id>([^<]+)<\/id>/)?.[1];
  if (!response.ok || !id) return Response.json({ message: 'Não foi possível criar a sessão PagBank.' }, { status: 502 });
  return Response.json({ id });
}
