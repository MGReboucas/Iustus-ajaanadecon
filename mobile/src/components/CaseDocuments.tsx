import { useState } from 'react';
import { Text, View } from 'react-native';
import { useSession } from '../auth/SessionProvider';
import { useResource } from '../lib/useResource';
import { errorMessage } from '../lib/api';
import { downloadDocument, pickDocument, uploadDocument } from '../lib/documents';
import type { DocumentVersion, Page } from '../lib/types';
import { Badge, Body, Button, Card, ErrorNotice, Loading, s } from './ui';

export function CaseDocuments({ caseId, closed, onChange }: { caseId: string; closed: boolean; onChange: () => Promise<void> }) {
  const { api } = useSession();
  const { data, error, loading, reload } = useResource<Page<DocumentVersion>>(`cases/${caseId}/documents`);
  const [extra, setExtra] = useState<DocumentVersion[]>([]);
  const [next, setNext] = useState<string | null | undefined>();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const [message, setMessage] = useState('');
  const rows = [...(data?.results || []), ...extra].filter((row, index, all) => all.findIndex(other => other.id === row.id) === index);
  const cursor = next === undefined ? data?.nextCursor : next;
  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setFailure('');
    try { await action(); } catch (e) { setFailure(errorMessage(e)); } finally { setBusy(false); }
  }
  async function upload(camera = false, previous?: DocumentVersion) {
    const file = await pickDocument(camera); if (!file) return;
    try {
      await uploadDocument(api, caseId, file, previous);
      setMessage('Arquivo recebido. Aguarde a verificação e atualize a lista antes de utilizá-lo.');
    } finally { setExtra([]); setNext(undefined); reload(); await onChange(); }
  }
  return <View style={{ gap: 14 }}><Text style={s.section} accessibilityRole="header">Documentos</Text>
    <Body>PDF, JPEG ou PNG, até 20 MiB. Os arquivos passam por verificação antes de serem liberados.</Body>
    <ErrorNotice message={failure || error} /><Body>{message}</Body>
    {!closed && <><Button title="Anexar arquivo" busy={busy} onPress={() => void run(() => upload())} />
      <Button title="Fotografar documento" secondary disabled={busy} onPress={() => void run(() => upload(true))} /></>}
    <Button title="Atualizar documentos" secondary disabled={busy} onPress={() => { setExtra([]); setNext(undefined); reload(); }} />
    {loading && <Loading />}
    {data && !rows.length && <Body>Nenhum documento enviado.</Body>}
    {rows.map(row => <Card key={row.id}><Text style={s.cardTitle}>{row.filename}</Text><Body>Versão {row.number}</Body><Badge success={row.status === 'AVAILABLE'}>{row.statusLabel}</Badge>
      {row.status === 'AVAILABLE' && <Button title={`Baixar ${row.filename}`} secondary disabled={busy} onPress={() => void run(() => downloadDocument(api, row))} />}
      {!closed && !rows.some(other => other.documentId === row.documentId && other.number > row.number) && <Button title={`Nova versão de ${row.filename}`} secondary disabled={busy} onPress={() => void run(() => upload(false, row))} />}
    </Card>)}
    {cursor && <Button title="Mais documentos" secondary busy={busy} onPress={() => void run(async () => {
      const page = await api<Page<DocumentVersion>>(`cases/${caseId}/documents?cursor=${encodeURIComponent(cursor)}`);
      setExtra(old => [...old, ...page.results]); setNext(page.nextCursor);
    })} />}
  </View>;
}
