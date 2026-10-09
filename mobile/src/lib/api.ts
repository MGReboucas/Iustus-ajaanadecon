export class ApiError extends Error {
  constructor(public code: string, message: string, public status = 0) { super(message); }
}

export function resolveOrigin(value: string | undefined, development: boolean): string {
  try {
    const url = new URL(value || '');
    const local = /^(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$/.test(url.hostname);
    if (url.username || url.password || url.pathname !== '/' || url.search || url.hash ||
        (url.protocol !== 'https:' && !(development && url.protocol === 'http:' && local))) throw new Error();
    return url.origin;
  } catch {
    throw new ApiError('NOT_CONFIGURED', 'O aplicativo ainda não está conectado ao serviço. Tente novamente mais tarde.');
  }
}

export function apiOrigin() {
  return resolveOrigin(process.env.EXPO_PUBLIC_API_ORIGIN, __DEV__);
}

export type RequestOptions = { method?: 'POST' | 'PATCH'; idempotencyKey?: string; binary?: boolean; download?: boolean };
export function validRoute(path: string) {
  const uuid = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
  return new RegExp(`^(?:auth/(?:login|logout|recovery|context|register|verify|resend|reset)|billing/(?:activate|resend|plan)|dashboard|me|privacy/requests|notifications(?:/${uuid}/read)?|cases(?:/catalog|/${uuid}(?:/(?:timeline|messages|submit|requests|workflow|documents(?:/uploads)?|proposals(?:/${uuid}/decision)?)|/requests/${uuid}/response)?)?|documents/${uuid}/versions(?:/${uuid}/content)?|uploads/${uuid}/(?:content|complete|authorize))(?:\\?cursor=[^#]*)?$`, 'i').test(path);
}
export async function request<T>(path: string, token?: string, body?: object, options: RequestOptions = {}): Promise<T> {
  if (!validRoute(path)) {
    throw new ApiError('INVALID_ROUTE', 'Não foi possível abrir esta página.');
  }
  const url = `${apiOrigin()}/api/v1/mobile/${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.binary || options.download ? 60000 : 20000);
  try {
    const response = await fetch(url, {
      method: options.method || (body === undefined ? 'GET' : 'POST'),
      credentials: 'omit', redirect: 'error', signal: controller.signal,
      headers: { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body === undefined ? {} : { 'Content-Type': options.binary ? 'application/octet-stream' : 'application/json' }),
        ...(options.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : {}) },
      body: body === undefined ? undefined : options.binary ? body as ArrayBuffer : JSON.stringify(body),
    });
    if (response.status === 204) return undefined as T;
    if (options.download && response.ok) return await response.arrayBuffer() as T;
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(data?.error?.code || 'REQUEST_FAILED',
        data?.error?.message || 'Não foi possível concluir. Tente novamente.', response.status);
    }
    if (!data || typeof data !== 'object') throw new ApiError('INVALID_RESPONSE', 'O serviço está indisponível. Tente novamente.');
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('NETWORK_ERROR', 'Não foi possível conectar. Confira sua internet e tente novamente.');
  } finally { clearTimeout(timer); }
}

export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.';
