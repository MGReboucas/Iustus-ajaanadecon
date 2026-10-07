import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import type { Session } from '../lib/types';

const key = 'iustus.mobile.session.v1';
const options = { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY };

// Preview web usa apenas memória. O produto web continua no frontend Next.js.
export async function readSession(): Promise<Session | null> {
  if (Platform.OS === 'web') return null;
  const raw = await SecureStore.getItemAsync(key, options);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    if (typeof data.origin !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(data.token) || !Number.isFinite(Date.parse(data.expiresAt))) return null;
    return data;
  } catch { return null; }
}

export async function saveSession(session: Session | null) {
  if (Platform.OS === 'web') return;
  if (session) await SecureStore.setItemAsync(key, JSON.stringify(session), options);
  else await SecureStore.deleteItemAsync(key, options);
}
