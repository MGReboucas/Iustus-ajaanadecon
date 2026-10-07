import { useCallback, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { randomUUID } from 'expo-crypto';
import { useSession } from '../auth/SessionProvider';
import { errorMessage } from '../lib/api';
import type { Message, Page } from '../lib/types';
import { Body, Button, Card, Empty, ErrorNotice, Field, Loading, s } from './ui';

export function CaseConversation({ caseId, canMessage }: { caseId: string; canMessage: boolean }) {
  const { api } = useSession();
  const [messages, setMessages] = useState<Message[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [sendError, setSendError] = useState('');
  const [draft, setDraft] = useState('');
  const generation = useRef(0);
  const reading = useRef(false);
  const writing = useRef(false);
  const pending = useRef<{ text: string; clientMessageId: string } | null>(null);
  const path = `cases/${caseId}/messages`;

  const load = useCallback(async (next?: string) => {
    if (reading.current || writing.current) return;
    reading.current = true;
    const run = generation.current;
    setLoading(true); setError('');
    try {
      const page = await api<Page<Message>>(`${path}${next ? `?cursor=${encodeURIComponent(next)}` : ''}`);
      if (run !== generation.current) return;
      setMessages(previous => next ? [...previous, ...page.results.filter(row => !previous.some(old => old.id === row.id))] : page.results);
      setCursor(page.nextCursor); setLoaded(true);
    } catch (err) { if (run === generation.current) setError(errorMessage(err)); }
    finally { if (run === generation.current) { reading.current = false; setLoading(false); } }
  }, [api, path]);

  useFocusEffect(useCallback(() => {
    void load();
    return () => { generation.current++; reading.current = false; writing.current = false; };
  }, [load]));

  async function send() {
    const text = draft.trim();
    if (!text || !canMessage || writing.current || reading.current) return;
    writing.current = true;
    const run = generation.current;
    setSending(true); setSendError('');
    try {
      // Keep the same key after an uncertain network result while the text is unchanged.
      if (pending.current?.text !== text) pending.current = { text, clientMessageId: randomUUID() };
      const message = await api<Message>(path, pending.current);
      if (run !== generation.current) return;
      setMessages(previous => [message, ...previous.filter(row => row.id !== message.id)]);
      setDraft(''); pending.current = null;
    } catch (err) { if (run === generation.current) setSendError(errorMessage(err)); }
    finally { if (run === generation.current) { writing.current = false; setSending(false); } }
  }

  return <View style={{ gap: 16 }}>
    <Text style={s.section} accessibilityRole="header">Conversa com o advogado</Text>
    <Button title="Atualizar conversa" secondary busy={loading} disabled={sending} onPress={() => void load()} />
    <ErrorNotice message={error} retry={() => void load(cursor || undefined)} />
    {loading && !loaded && <Loading />}
    {loaded && !messages.length && <Empty title="Nenhuma mensagem" message="As mensagens deste atendimento aparecerão aqui." />}
    {messages.map(message => <Card key={message.id}>
      <Text style={s.cardTitle}>{message.authorName || 'Participante do atendimento'}</Text>
      <Text style={s.caption}>{new Date(message.createdAt).toLocaleString('pt-BR')}</Text>
      <Body>{message.text}</Body>
    </Card>)}
    {cursor && <Button title="Ver mensagens anteriores" secondary busy={loading} disabled={sending} onPress={() => void load(cursor)} />}
    {canMessage ? <Card>
      <Field label="Sua mensagem" value={draft} onChangeText={setDraft} multiline maxLength={10000} editable={!sending} style={[s.input, { minHeight: 112, textAlignVertical: 'top' }]} />
      <Text style={s.caption}>{draft.length}/10000 caracteres</Text>
      <ErrorNotice message={sendError} />
      <Button title="Enviar mensagem" busy={sending} disabled={!draft.trim() || loading || !loaded} onPress={() => void send()} />
    </Card> : <Body>O envio de mensagens fica disponível após a atribuição de um advogado, enquanto o caso está em atendimento.</Body>}
  </View>;
}
