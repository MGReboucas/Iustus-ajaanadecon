import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { Switch, Text, View } from 'react-native';
import { useSession } from '../auth/SessionProvider';
import { errorMessage } from '../lib/api';
import { downloadDocument } from '../lib/documents';
import type { Case, Dashboard, DocumentVersion, InformationRequest, LegalWorkflow, Page } from '../lib/types';
import { Badge, Body, Button, Card, ErrorNotice, Field, Loading, s } from './ui';

export function CaseWork({ item, onChange }: { item: Case; onChange: () => Promise<void> }) {
  const { api } = useSession();
  const [work, setWork] = useState<LegalWorkflow>();
  const [requests, setRequests] = useState<InformationRequest[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentVersion[]>([]);
  const [docCursor, setDocCursor] = useState<string | null>(null);
  const [owner, setOwner] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const load = useCallback(async () => {
    const run = ++generation.current; setLoading(true); setError('');
    try {
      const [flow, pending, files, dashboard] = await Promise.all([
        api<LegalWorkflow>(`cases/${item.id}/workflow`), api<Page<InformationRequest>>(`cases/${item.id}/requests`),
        api<Page<DocumentVersion>>(`cases/${item.id}/documents`), api<Dashboard>('dashboard'),
      ]);
      if (run !== generation.current) return;
      setWork(flow); setRequests(pending.results); setCursor(pending.nextCursor); setDocuments(files.results); setDocCursor(files.nextCursor);
      setOwner(dashboard.user.id); setSelected([]);
    } catch (e) { if (run === generation.current) setError(errorMessage(e)); }
    finally { if (run === generation.current) setLoading(false); }
  }, [api, item.id]);
  useFocusEffect(useCallback(() => { void load(); return () => { generation.current++; }; }, [load]));
  async function run(action: () => Promise<void>) {
    if (busy) return; setBusy(true); setError(''); setMessage('');
    try { await action(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const editable = !['RASCUNHO', 'RECUSADO', 'ENCERRADO'].includes(item.state);
  const needsSelection = editable && (item.state === 'AGUARDANDO_PROCURACAO' && !work?.signedMandate || requests.some(row => !row.responded && !row.resolved));
  return <View style={{ gap: 14 }}><Text style={s.section} accessibilityRole="header">Etapas e pendências</Text>
    <ErrorNotice message={error} retry={() => void load()} />{!!message && <Body>{message}</Body>}
    <Button title="Atualizar etapas" secondary disabled={busy} onPress={() => void load()} />
    {loading && <Loading />}
    {needsSelection && <Card><Text style={s.cardTitle}>Selecionar documentos verificados</Text><Body>Anexe os arquivos na seção Documentos. Depois de verificados, selecione-os aqui para responder uma pendência ou entregar a procuração.</Body>
      {documents.filter(row => row.status === 'AVAILABLE' && row.uploadedById === owner).map(row => <View key={row.id}><Body>{row.filename} · versão {row.number}</Body>
        <Switch accessibilityLabel={`Selecionar ${row.filename} versão ${row.number}`} value={selected.includes(row.id)} disabled={busy || loading} onValueChange={value => setSelected(old => value ? [...old, row.id] : old.filter(id => id !== row.id))} /></View>)}
      {docCursor && <Button title="Mais arquivos para selecionar" secondary disabled={busy} onPress={() => void run(async () => {
        const page = await api<Page<DocumentVersion>>(`cases/${item.id}/documents?cursor=${encodeURIComponent(docCursor)}`);
        setDocuments(old => [...old, ...page.results]); setDocCursor(page.nextCursor);
      })} />}
    </Card>}
    {requests.map(row => <Card key={row.id}><Text style={s.cardTitle}>{row.description}</Text>
      <Badge>{row.resolved ? 'Conferida' : row.responded ? 'Aguardando conferência' : 'Resposta necessária'}</Badge>
      {!!row.response && <Body>Sua resposta: {row.response}</Body>}{!!row.resolution && <Body>Conferência: {row.resolution}</Body>}
      {row.attachments.map(file => <Button key={file.id} title={`Baixar ${file.filename}`} secondary disabled={busy} onPress={() => void run(() => downloadDocument(api, file))} />)}
      {!row.responded && !row.resolved && item.state === 'AGUARDANDO_CLIENTE' && <>
        <Field label="Resposta ao complemento" multiline value={text[row.id] || ''} maxLength={10000} editable={!busy} onChangeText={value => setText(old => ({ ...old, [row.id]: value }))} />
        <Button title="Enviar complemento" busy={busy} disabled={loading || (text[row.id] || '').trim().length < 5 || selected.length > 20} onPress={() => void run(async () => {
          const current = await api<Case>(`cases/${item.id}`);
          await api(`cases/${item.id}/requests/${row.id}/response`, { version: current.version, text: text[row.id], documentVersionIds: selected });
          setMessage('Complemento enviado para conferência.'); await load(); await onChange();
        })} />
      </>}
    </Card>)}
    {cursor && <Button title="Mais pendências" secondary busy={busy} onPress={() => void run(async () => {
      const page = await api<Page<InformationRequest>>(`cases/${item.id}/requests?cursor=${encodeURIComponent(cursor)}`);
      setRequests(old => [...old, ...page.results]); setCursor(page.nextCursor);
    })} />}
    {work?.scope ? <Card><Text style={s.cardTitle}>Atendimento contratado</Text><Body>{work.scope}</Body>
      {!!work.authority && <Body>Órgão: {work.authority}</Body>}{!!work.processNumber && <Body>Processo: {work.processNumber}</Body>}
      {work.mandate && <Button title="Baixar procuração para assinatura" secondary disabled={busy} onPress={() => void run(() => downloadDocument(api, work.mandate!))} />}
      {work.signedMandate ? <><Body>Procuração entregue para conferência.</Body><Button title="Baixar procuração entregue" secondary disabled={busy} onPress={() => void run(() => downloadDocument(api, work.signedMandate!))} /></> : item.state === 'AGUARDANDO_PROCURACAO' && <>
        <Body>Assine conforme a orientação do advogado, anexe o arquivo e selecione apenas a versão assinada e verificada.</Body>
        <Button title="Entregar procuração assinada" disabled={loading || selected.length !== 1} busy={busy} onPress={() => void run(async () => {
          const current = await api<Case>(`cases/${item.id}`);
          await api(`cases/${item.id}/workflow`, { version: current.version, action: 'SIGN', documentId: selected[0] });
          setMessage('Procuração enviada para conferência.'); await load(); await onChange();
        })} />
      </>}
      {!!work.publishedText && <><Text style={s.cardTitle}>Peça publicada</Text><Text selectable style={s.body}>{work.publishedText}</Text></>}
      {!!work.protocol && <Body>Protocolo: {work.protocol}</Body>}
      {work.receipt && <Button title="Baixar comprovante de protocolo" secondary disabled={busy} onPress={() => void run(() => downloadDocument(api, work.receipt!))} />}
    </Card> : !loading && <Body>As etapas do atendimento aparecerão após a análise do caso.</Body>}
    {work?.tasks.map(task => <Card key={task.id}><Text style={s.cardTitle}>{task.title}</Text><Body>{new Date(task.dueAt).toLocaleString('pt-BR')}</Body><Badge>{task.completedAt ? 'Concluído' : 'Agendado'}</Badge>{!!task.outcome && <Body>{task.outcome}</Body>}</Card>)}
  </View>;
}
