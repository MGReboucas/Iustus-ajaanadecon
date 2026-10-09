import { useState } from 'react';
import { Text } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../../auth/SessionProvider';
import { useResource } from '../../lib/useResource';
import { errorMessage } from '../../lib/api';
import type { Notice, Page } from '../../lib/types';
import { Badge, Body, Button, Card, ErrorNotice, Loading, Screen, Title, s } from '../../components/ui';
export default function Notices() {
  const { api } = useSession(); const { data, error, loading, reload } = useResource<Page<Notice>>('notifications');
  const [extra, setExtra] = useState<Notice[]>([]); const [next, setNext] = useState<string | null | undefined>();
  const [busy, setBusy] = useState(false); const [failure, setFailure] = useState('');
  const cursor = next === undefined ? data?.nextCursor : next;
  async function run(action: () => Promise<void>) { if (busy) return; setBusy(true); setFailure(''); try { await action(); } catch (e) { setFailure(errorMessage(e)); } finally { setBusy(false); } }
  return <Screen><Title>Avisos</Title><ErrorNotice message={failure || error} />
    <Button title="Atualizar avisos" secondary onPress={() => { setExtra([]); setNext(undefined); void reload(); }} />
    {loading && <Loading />}{data && !data.results.length && <Body>Nenhum aviso por enquanto.</Body>}
    {[...(data?.results || []), ...extra].filter((row, index, all) => all.findIndex(other => other.id === row.id) === index).map(row => <Card key={row.id}>
      <Badge>{row.readAt ? 'Lido' : 'Novo'}</Badge><Text style={s.cardTitle}>{row.title}</Text><Body>{new Date(row.createdAt).toLocaleString('pt-BR')} · #{row.reference}</Body>
      <Button title="Abrir caso do aviso" disabled={busy} onPress={() => void run(async () => { await api(`notifications/${row.id}/read`, {}); router.push({ pathname: '/case/[id]', params: { id: row.caseId } }); })} />
    </Card>)}
    {cursor && <Button title="Mais avisos" secondary busy={busy} onPress={() => void run(async () => { const page = await api<Page<Notice>>(`notifications?cursor=${encodeURIComponent(cursor)}`); setExtra(old => [...old, ...page.results]); setNext(page.nextCursor); })} />}
  </Screen>;
}
