import { useCallback, useRef, useState } from 'react';
import { AppState } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { useSession } from '../auth/SessionProvider';
import { errorMessage } from './api';

export function useResource<T>(path: string) {
  const { api } = useSession();
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const load = useCallback(async () => {
    const run = ++generation.current;
    setLoading(true); setError('');
    try { const value = await api<T>(path); if (run === generation.current) setData(value); }
    catch (err) { if (run === generation.current) setError(errorMessage(err)); }
    finally { if (run === generation.current) setLoading(false); }
  }, [api, path]);
  useFocusEffect(useCallback(() => {
    void load();
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') void load(); });
    return () => { generation.current++; subscription.remove(); };
  }, [load]));
  return { data, loading, error, reload: load };
}
