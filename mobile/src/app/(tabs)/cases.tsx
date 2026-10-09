import { useCallback, useRef, useState } from 'react';
import { FlatList, Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useSession } from '../../auth/SessionProvider';
import type { Case, Page } from '../../lib/types';
import { errorMessage } from '../../lib/api';
import { CaseCard } from '../../components/CaseCard';
import { Body, Button, colors, Empty, ErrorNotice, Label, Loading, Title, s } from '../../components/ui';

export default function Cases() {
  const { api } = useSession();
  const [items, setItems] = useState<Case[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const busy = useRef(false);
  const load = useCallback(async (next?: string) => {
    if (next && busy.current) return;
    busy.current = true;
    const run = ++generation.current;
    setLoading(true); setError('');
    try {
      const result = await api<Page<Case>>('cases' + (next ? `?cursor=${encodeURIComponent(next)}` : ''));
      if (run !== generation.current) return;
      setItems(previous => next ? [...previous, ...result.results.filter(row => !previous.some(old => old.id === row.id))] : result.results);
      setCursor(result.nextCursor); setLoaded(true);
    } catch (err) { if (run === generation.current) setError(errorMessage(err)); }
    finally { if (run === generation.current) { setLoading(false); busy.current = false; } }
  }, [api]);
  useFocusEffect(useCallback(() => { void load(); return () => { generation.current++; busy.current = false; }; }, [load]));
  return <SafeAreaView style={s.fill} edges={['top', 'left', 'right']}><FlatList data={items} keyExtractor={item => item.id} contentContainerStyle={s.page}
    renderItem={({ item }) => <CaseCard item={item} />} refreshing={loading && loaded} onRefresh={() => void load()}
    ListHeaderComponent={<View style={{ gap: 16 }}><View><Label>ACOMPANHAMENTO</Label><Title>Meus casos</Title></View><Body>Consulte o andamento e o histórico dos seus atendimentos.</Body><Button title="Nova ocorrência" onPress={() => router.push('/new-case')} /><ErrorNotice message={error} retry={() => void load()} /></View>}
    ListEmptyComponent={loading ? <Loading /> : loaded ? <Empty title="Seus casos aparecerão aqui" message="Você ainda não tem ocorrências cadastradas. Os casos enviados pelo site também ficam disponíveis neste aplicativo." /> : null}
    ListFooterComponent={cursor ? <Button title="Carregar mais casos" secondary busy={loading} onPress={() => void load(cursor)} /> : items.length ? <Text style={{ color: colors.muted, textAlign: 'center' }}>Todos os casos foram carregados.</Text> : null} />
  </SafeAreaView>;
}
