import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const routes = new Set([
  "auth/csrf", "auth/register", "auth/verify", "auth/resend", "auth/login",
  "auth/logout", "auth/recovery", "auth/reset", "auth/mfa/enroll", "auth/mfa/verify",
  "auth/invitations/accept", "admin/invitations", "me", "dashboard/client", "dashboard/team",
  "cases", "cases/catalog", "cases/lawyers",
]);
const uuid = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const caseRoute = new RegExp(`^cases/${uuid}(?:/(?:submit|assignment|transitions|requests|timeline)|/requests/${uuid}/(?:response|resolve))?$`, "i");
const documentRoute = new RegExp(`^(?:cases/${uuid}/documents(?:/uploads)?|documents/${uuid}/versions(?:/${uuid}/(?:download|content))?|uploads/${uuid}/(?:content|complete))$`, "i");
const uploadRoute = new RegExp(`^uploads/${uuid}/content$`, "i");
const downloadRoute = new RegExp(`^documents/${uuid}/versions/${uuid}/content$`, "i");

function failure(code: string, message: string, status: number) {
  return Response.json({ error: { code, message, fields: {} } }, {
    status, headers: { "Cache-Control": "no-store, private", "Referrer-Policy": "no-referrer" },
  });
}

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  if (!routes.has(path) && !caseRoute.test(path) && !documentRoute.test(path)) return failure("NOT_FOUND", "Recurso não encontrado.", 404);
  const origin = process.env.DJANGO_API_ORIGIN;
  const key = process.env.IUSTUS_PROXY_SECRET;
  const portals = [process.env.IUSTUS_CLIENT_ORIGIN, process.env.IUSTUS_TEAM_ORIGIN].filter(Boolean) as string[];
  if (!origin || !key || portals.length !== 2) return failure("NOT_CONFIGURED", "O acesso ainda não foi configurado.", 503);
  const host = request.headers.get("host")?.toLowerCase();
  const portal = portals.find(value => new URL(value).host.toLowerCase() === host);
  if (!portal) return failure("INVALID_PORTAL", "Portal não permitido.", 403);
  const headers = new Headers({ "Accept": "application/json", "X-Iustus-Portal-Host": host!, "X-Iustus-Proxy-Key": key });
  // Somente os headers abaixo atravessam a fronteira. Forwarded, X-Forwarded-* e
  // X-Iustus-* do navegador são descartados; cookies continuam vinculados ao host.
  for (const name of ["cookie", "origin", "referer", "x-csrftoken", "content-type", "idempotency-key"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  let body: Uint8Array | undefined;
  if (request.method !== "GET") {
    const binary = uploadRoute.test(path) && request.method === "POST";
    const type = binary ? "application/octet-stream" : "application/json";
    if (request.headers.get("content-type")?.split(";")[0].trim() !== type) return failure("INVALID_INPUT", binary ? "Envie o conteúdo do arquivo." : "Envie dados JSON.", 415);
    const limit = binary ? 20 * 1024 * 1024 : 262144;
    if (Number(request.headers.get("content-length")) > limit) return failure("PAYLOAD_TOO_LARGE", "Solicitação muito grande.", 413);
    const reader = request.body?.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    if (reader) {
      while (true) {
        const next = await reader.read();
        if (next.done) break;
        size += next.value.byteLength;
        if (size > limit) { await reader.cancel(); return failure("PAYLOAD_TOO_LARGE", "Solicitação muito grande.", 413); }
        chunks.push(next.value);
      }
    }
    body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
  }
  try {
    const url = new URL(`/api/v1/${path}`, origin);
    for (const name of ["cursor", "state", ...(downloadRoute.test(path) ? ["token"] : [])]) {
      const value = request.nextUrl.searchParams.get(name);
      if (value) url.searchParams.set(name, value);
    }
    const upstream = await fetch(url, {
      method: request.method, headers, body: body as BodyInit | undefined,
      cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(documentRoute.test(path) ? 60000 : 15000),
    });
    if (upstream.status >= 300 && upstream.status < 400) return failure("UPSTREAM_ERROR", "Serviço indisponível.", 502);
    // Nunca retransmitir páginas DEBUG/HTML ou stack trace do backend.
    if (upstream.status >= 500) return failure("UPSTREAM_ERROR", "Não foi possível concluir. Tente novamente.", 502);
    const outgoing = new Headers({ "Cache-Control": "no-store, private", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff" });
    for (const name of ["content-type", "retry-after", ...(downloadRoute.test(path) ? ["content-disposition", "content-security-policy"] : [])]) {
      const value = upstream.headers.get(name);
      if (value) outgoing.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie()) outgoing.append("set-cookie", cookie);
    return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: outgoing });
  } catch {
    return failure("SERVICE_UNAVAILABLE", "O serviço de acesso está temporariamente indisponível.", 503);
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
