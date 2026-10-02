import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const response = path === "/cliente" || path.startsWith("/cliente/")
    ? NextResponse.redirect(new URL("/acessar", request.url))
    : NextResponse.next();
  response.headers.set("Cache-Control", "no-store, private");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.set("X-Frame-Options", "DENY");
  return response;
}

export const config = { matcher: ["/acessar", "/cliente/:path*", "/advogado/:path*"] };
