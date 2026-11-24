import { apiOrigin } from './api';
import { Linking } from 'react-native';

export async function openPortal(path: '/privacidade' | '/termos' | '/checkout' | '/acessar') {
  await Linking.openURL(`${apiOrigin()}${path}`);
}

export function readAccessLink(value: string): { mode: 'verify' | 'reset' | 'member'; token: string } {
  const url = new URL(value.trim());
  const origin = apiOrigin();
  const production = ['https://www.iustus.app', 'https://iustus.app'];
  const web = (url.origin === origin || production.includes(origin) && production.includes(url.origin)) && url.pathname === '/acessar';
  const native = url.protocol === 'iustus:' && (url.hostname === 'access' && !url.pathname || !url.hostname && url.pathname === '/access');
  if ((!web && !native) || url.username || url.password || url.search) throw new Error('Use o link enviado pelo Íustus.');
  const fragment = new URLSearchParams(url.hash.slice(1));
  if (Array.from(fragment.keys()).length !== 1) throw new Error('Use um único link de acesso completo.');
  for (const mode of ['verify', 'reset', 'member'] as const) {
    const token = fragment.get(mode);
    if (token && /^[A-Za-z0-9_-]{43}$/.test(token)) return { mode, token };
  }
  throw new Error('O link não contém um código de acesso válido. Copie o endereço completo do e-mail.');
}
