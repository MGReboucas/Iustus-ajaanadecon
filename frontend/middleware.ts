import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  if (request.nextUrl.hostname === "iustus-defesa-juridica.vercel.app") {
    const destination = request.nextUrl.clone();
    destination.protocol = "https:";
    destination.host = "iustus.app";
    destination.port = "";
    const redirect = NextResponse.redirect(destination, 307);
    redirect.headers.set("Cache-Control", "no-store, private");
    redirect.headers.set("Referrer-Policy", "no-referrer");
    return redirect;
  }
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store, private");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.set("X-Frame-Options", "DENY");
  return response;
}

export const config = { matcher: ["/acessar", "/cliente/:path*", "/advogado/:path*"] };
