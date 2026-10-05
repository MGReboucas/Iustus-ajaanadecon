// Substituído pelo checkout hospedado: nenhum cartão é recebido nesta rota.
export async function POST() {
  return Response.json({ message: 'Use a página de adesão para iniciar um pagamento.' }, { status: 410, headers: { 'Cache-Control': 'no-store' } });
}
