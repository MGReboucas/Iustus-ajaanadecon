"use client";

export type Portal = "client" | "team";
export type Profile = { id: string; name: string; email: string; caseEmailEnabled: boolean; role: "CLIENT" | "LAWYER" | "ADMIN" };
export type Context = { csrfToken: string; portal: Portal; policyVersion: string; mfaRequired: boolean; registrationAvailable: boolean };

export class ApiError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

export async function api<T>(path: string, body?: object, options?: { method?: "POST" | "PATCH"; idempotencyKey?: string }): Promise<T> {
  let csrfToken: string | undefined;
  if (body !== undefined) {
    // Buscar por mutação evita reutilizar token anterior ao login/rotação de sessão.
    const context = await api<Context>("auth/csrf");
    csrfToken = context.csrfToken;
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, {
      method: body === undefined ? "GET" : options?.method || "POST", credentials: "same-origin", cache: "no-store",
      headers: body === undefined ? undefined : { "Content-Type": "application/json", "X-CSRFToken": csrfToken!, ...(options?.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch { throw new ApiError("NETWORK_ERROR", "Não foi possível conectar. Tente novamente."); }
  const result = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(result?.error?.code ?? "REQUEST_FAILED", result?.error?.message ?? "Não foi possível concluir a solicitação.");
  return result as T;
}
