import { apiOrigin } from './api';
import { Linking } from 'react-native';

export async function openPortal(path: '/privacidade' | '/termos' | '/checkout' | '/acessar') {
  await Linking.openURL(`${apiOrigin()}${path}`);
}

export function readAccessLink(value: string): { mode: 'verify' | 'reset' | 'member'; token: string } {
  const url = new URL(value.trim());
  if (url.origin !== apiOrigin() && url.protocol !== 'iustus:') throw new Error('Use o link enviado pelo Íustus.');
  const fragment = new URLSearchParams(url.hash.slice(1));
  for (const mode of ['verify', 'reset', 'member'] as const) {
    const token = fragment.get(mode);
    if (token && /^[A-Za-z0-9_-]{43}$/.test(token)) return { mode, token };
  }
  throw new Error('O link não contém um código de acesso válido. Copie o endereço completo do e-mail.');
}
