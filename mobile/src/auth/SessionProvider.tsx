import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { ApiError, apiOrigin, request } from '../lib/api';
import type { Profile, Session } from '../lib/types';
import { readSession, saveSession } from './storage';

type Auth = {
  ready: boolean; signedIn: boolean; storageError: string;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  api: <T>(path: string, body?: object) => Promise<T>;
};
const Context = createContext<Auth | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [storageError, setStorageError] = useState('');
  const current = useRef<Session | null>(null);
  const storageQueue = useRef(Promise.resolve());
  const persist = useCallback((value: Session | null) => {
    const next = storageQueue.current.catch(() => {}).then(() => saveSession(value));
    storageQueue.current = next;
    return next;
  }, []);
  const clear = useCallback(async () => {
    current.current = null; setSession(null);
    try { await persist(null); return true; }
    catch {
      setStorageError('Não foi possível limpar o acesso salvo neste aparelho. Tente novamente quando o aparelho estiver desbloqueado.');
      return false;
    }
  }, [persist]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const saved = await readSession();
        if (saved && saved.origin === apiOrigin() && Date.parse(saved.expiresAt) > Date.now()) {
          if (mounted) { current.current = saved; setSession(saved); }
        } else await persist(null);
      } catch { if (mounted) setStorageError('Não foi possível recuperar seu acesso. Entre novamente.'); }
      finally { if (mounted) setReady(true); }
    })();
    return () => { mounted = false; };
  }, [persist]);

  const api = useCallback(async <T,>(path: string, body?: object) => {
    const active = current.current;
    if (!active) throw new ApiError('AUTH_REQUIRED', 'Entre novamente para continuar.', 401);
    if (Date.parse(active.expiresAt) <= Date.now()) {
      await clear(); throw new ApiError('AUTH_REQUIRED', 'Sua sessão expirou. Entre novamente.', 401);
    }
    try {
      const result = await request<T>(path, active.token, body);
      if (current.current !== active) throw new ApiError('AUTH_REQUIRED', 'Sua sessão foi encerrada.', 401);
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401 && current.current === active) await clear();
      throw error;
    }
  }, [clear]);

  const signIn = useCallback(async (email: string, password: string) => {
    const response = await request<{ token: string; expiresAt: string; user: Profile }>('auth/login', undefined, { email: email.trim(), password });
    const value = { token: response.token, expiresAt: response.expiresAt, origin: apiOrigin() };
    try { await persist(value); }
    catch {
      await request('auth/logout', value.token, {}).catch(() => {});
      throw new Error('Não foi possível guardar seu acesso com segurança. Tente novamente.');
    }
    setStorageError(''); current.current = value; setSession(value);
  }, [persist]);

  const signOut = useCallback(async () => {
    const active = current.current;
    let failure: unknown;
    try { if (active) await request('auth/logout', active.token, {}); }
    catch (error) { if (!(error instanceof ApiError && error.status === 401)) failure = error; }
    const removed = await clear();
    if (!removed) throw new Error('Não foi possível remover o acesso salvo. Desbloqueie o aparelho e tente novamente.');
    if (failure) throw new Error('Você saiu deste aparelho. Não foi possível confirmar o encerramento no servidor; a sessão restante expira automaticamente.');
  }, [clear]);

  return <Context.Provider value={{ ready, signedIn: !!session, storageError, signIn, signOut, api }}>{children}</Context.Provider>;
}

export function useSession() {
  const value = useContext(Context);
  if (!value) throw new Error('SessionProvider ausente');
  return value;
}
