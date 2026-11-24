import { useState } from 'react';
import { Text } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../../auth/SessionProvider';
import { usePagedResource } from '../../lib/usePagedResource';
import { errorMessage } from '../../lib/api';
import type { Notice } from '../../lib/types';
import { Badge, Body, Button, Card, ErrorNotice, Loading, Screen, Title, s } from '../../components/ui';
export default function Notices() {
  const { api } = useSession(); const { data, rows, cursor, loadMore, moreLoading, moreError, error, loading, reload } = usePagedResource<Notice>('notifications');
  const [busy, setBusy] = useState(false); const [failure, setFailure] = useState('');
  async function run(action: () => Promise<void>) { if (busy) return; setBusy(true); setFailure(''); try { await action(); } catch (e) { setFailure(errorMessage(e)); } finally { setBusy(false); } }
  return <Screen><Title>Avisos</Title><ErrorNotice message={failure || moreError || error} />
    <Button title="Atualizar avisos" secondary disabled={busy || loading || moreLoading} onPress={() => void reload()} />
    {loading && <Loading />}{data && !data.results.length && <Body>Nenhum aviso por enquanto.</Body>}
    {rows.map(row => <Card key={row.id}>
      <Badge>{row.readAt ? 'Lido' : 'Novo'}</Badge><Text style={s.cardTitle}>{row.title}</Text><Body>{new Date(row.createdAt).toLocaleString('pt-BR')} · #{row.reference}</Body>
      <Button title="Abrir caso do aviso" disabled={busy} onPress={() => void run(async () => { await api(`notifications/${row.id}/read`, {}); router.push({ pathname: '/case/[id]', params: { id: row.caseId } }); })} />
    </Card>)}
    {cursor && <Button title="Mais avisos" secondary busy={moreLoading} disabled={busy || loading} onPress={() => void loadMore()} />}
  </Screen>;
}
