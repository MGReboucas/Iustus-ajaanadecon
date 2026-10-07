import { useCallback, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useSession } from '../../auth/SessionProvider';
import { CaseConversation } from '../../components/CaseConversation';
import type { Case, CaseEvent, Page } from '../../lib/types';
import { errorMessage } from '../../lib/api';
import { Badge, Body, Button, Card, date, Empty, ErrorNotice, Label, Loading, Screen, Title, s } from '../../components/ui';

const events: Record<string, string> = { DRAFT_CREATED: 'Rascunho criado', DRAFT_UPDATED: 'Rascunho atualizado', SUBMITTED: 'Ocorrência enviada', TRIAGE_STARTED: 'Análise iniciada', TRIAGE_DECISION: 'Análise atualizada', INFORMATION_REQUESTED: 'Complemento solicitado', INFORMATION_RESPONDED: 'Complemento enviado', INFORMATION_RESOLVED: 'Complemento analisado', MANDATE_REQUESTED: 'Procuração solicitada', MANDATE_SIGNED: 'Procuração assinada' };

export default function Detail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { api } = useSession();
  const [item, setItem] = useState<Case>();
  const [timeline, setTimeline] = useState<CaseEvent[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const busy = useRef(false);
  const load = useCallback(async (next?: string) => {
    if (next && busy.current) return;
    busy.current = true;
    const run = ++generation.current;
    setLoading(true); setError('');
    try {
      if (!/^[0-9a-f-]{36}$/i.test(id || '')) throw new Error('Este caso não foi encontrado.');
      const [detail, history] = await Promise.all([
        next ? Promise.resolve(undefined) : api<Case>(`cases/${id}`),
        api<Page<CaseEvent>>(`cases/${id}/timeline${next ? `?cursor=${encodeURIComponent(next)}` : ''}`),
      ]);
      if (run !== generation.current) return;
      if (detail) setItem(detail);
      setTimeline(previous => next ? [...previous, ...history.results.filter(row => !previous.some(old => old.id === row.id))] : history.results);
      setCursor(history.nextCursor);
    } catch (err) { if (run === generation.current) setError(errorMessage(err)); }
    finally { if (run === generation.current) { setLoading(false); busy.current = false; } }
  }, [api, id]);
  useFocusEffect(useCallback(() => { setItem(undefined); setTimeline([]); void load(); return () => { generation.current++; busy.current = false; }; }, [load]));
  return <Screen><ErrorNotice message={error} retry={() => void load()} />{!item ? (loading ? <Loading /> : null) : <>
    <View><Label>CASO #{item.reference}</Label><Title>{item.title || 'Rascunho sem título'}</Title></View><Badge>{item.stateLabel}</Badge>
    <Card><Label>INFORMAÇÕES DO CASO</Label><Body>{item.categoryLabel || 'Categoria não definida'}</Body><Body>Cadastrado em {date(item.createdAt)}</Body>{item.occurredOn && <Body>Data do ocorrido: {date(item.occurredOn)}</Body>}</Card>
    <Card><Text style={s.cardTitle}>Seu relato</Text><Body>{item.description || 'O relato ainda não foi preenchido.'}</Body></Card>
    <CaseConversation key={id} caseId={id} canMessage={item.canMessage === true} />
    <Text style={s.section} accessibilityRole="header">Histórico do atendimento</Text>
    {timeline.length ? timeline.map(event => <Card key={event.id}><Text style={s.caption}>{date(event.createdAt)}</Text><Text style={s.cardTitle}>{events[event.action] || 'Atualização do atendimento'}</Text>{!!event.reason && <Body>{event.reason}</Body>}</Card>) : <Empty title="Aguardando movimentações" message="As atualizações do atendimento aparecerão aqui." />}
    {cursor && <Button title="Ver movimentações anteriores" secondary busy={loading} onPress={() => void load(cursor)} />}
  </>}</Screen>;
}
