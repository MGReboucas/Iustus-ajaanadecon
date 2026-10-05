// Sessões do checkout transparente legado foram desativadas.
export async function GET() {
  return Response.json({ message: 'Use a página de adesão.' }, { status: 410, headers: { 'Cache-Control': 'no-store' } });
}
