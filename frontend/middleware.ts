import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const response = path === "/" || path.startsWith("/cliente") || path.startsWith("/checkout")
    ? NextResponse.redirect(new URL("/acessar", request.url))
    : NextResponse.next();
  response.headers.set("Cache-Control", "no-store, private");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.set("X-Frame-Options", "DENY");
  return response;
}

export const config = { matcher: ["/", "/checkout/:path*", "/acessar", "/cliente/:path*", "/advogado/:path*"] };
