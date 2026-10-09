import { useRef, useState } from 'react';
import { Switch, View } from 'react-native';
import * as Crypto from 'expo-crypto';
import { useSession } from '../auth/SessionProvider';
import { useResource } from '../lib/useResource';
import type { Case, CaseCatalog } from '../lib/types';
import { errorMessage } from '../lib/api';
import { Body, Button, Card, ErrorNotice, Field } from './ui';

export function CaseDraft({ item, onSaved }: { item?: Case; onSaved: (item: Case) => Promise<void> | void }) {
  const { api } = useSession();
  const catalog = useResource<CaseCatalog>('cases/catalog');
  const [title, setTitle] = useState(item?.title || '');
  const [description, setDescription] = useState(item?.description || '');
  const [category, setCategory] = useState(item?.category || '');
  const [occurredOn, setOccurredOn] = useState(item?.occurredOn || '');
  const [acknowledged, setAcknowledged] = useState(item?.scopeAcknowledged || false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submission = useRef<{ version: number; key: string } | null>(null);
  const dirty = item && (title !== item.title || description !== item.description || category !== item.category || occurredOn !== (item.occurredOn || '') || acknowledged !== item.scopeAcknowledged);
  async function save() {
    if (busy) return;
    setBusy(true); setError('');
    try {
      if (occurredOn && !/^\d{4}-\d{2}-\d{2}$/.test(occurredOn)) throw new Error('Informe a data no formato AAAA-MM-DD.');
      const body = { title, description, category, occurredOn: occurredOn || null, scopeAcknowledged: acknowledged };
      const result = await api<Case>(item ? `cases/${item.id}` : 'cases', { ...body, ...(item ? { version: item.version } : {}) }, item ? { method: 'PATCH' } : undefined);
      await onSaved(result);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function submit() {
    if (!item || busy) return;
    setBusy(true); setError('');
    try {
      if (!submission.current || submission.current.version !== item.version) submission.current = { version: item.version, key: Crypto.randomUUID() };
      const result = await api<Case>(`cases/${item.id}/submit`, { version: item.version }, { idempotencyKey: submission.current.key });
      await onSaved(result);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <Card><Field label="Título da ocorrência" value={title} onChangeText={setTitle} maxLength={160} editable={!busy} />
    <Body>Categoria</Body><View style={{ gap: 8 }}>{catalog.data?.categories.map(row => <Button key={row.id} title={`${category === row.id ? '✓ ' : ''}${row.label}`} secondary={category !== row.id} disabled={busy} onPress={() => setCategory(row.id)} />)}</View>
    <Field label="Data do ocorrido (AAAA-MM-DD)" value={occurredOn} onChangeText={setOccurredOn} maxLength={10} editable={!busy} />
    <Field label="Relato do ocorrido" value={description} onChangeText={setDescription} multiline numberOfLines={6} maxLength={20000} editable={!busy} />
    <Body>Entendo que o envio passa por triagem. Honorários, custas e despesas dependem de contratação específica; a associação não garante aceite ou resultado.</Body>
    <Switch accessibilityLabel="Ciência do escopo do atendimento" value={acknowledged} onValueChange={setAcknowledged} disabled={busy} />
    <ErrorNotice message={error || catalog.error} retry={catalog.reload} />
    <Button title={item ? 'Salvar alterações' : 'Salvar ocorrência e anexar documentos'} busy={busy} onPress={() => void save()} />
    {item && <><Body>{catalog.data?.submission.message}</Body>
      <Body>{dirty ? 'Salve suas alterações antes de enviar.' : 'Confira o relato e os documentos. Após o envio, o rascunho não poderá ser editado.'}</Body>
      {catalog.data?.intakeRequired && <Body>É necessário informar a data e ter pelo menos um documento verificado.</Body>}
      <Button title="Enviar ocorrência para triagem" disabled={!!dirty || !catalog.data?.submission.canSubmit} busy={busy} onPress={() => void submit()} /></>}
  </Card>;
}
