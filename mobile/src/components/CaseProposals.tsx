import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { Switch, Text, View } from 'react-native';
import { useSession } from '../auth/SessionProvider';
import { errorMessage } from '../lib/api';
import type { Case, Page, ServiceProposal } from '../lib/types';
import { Body, Button, Card, ErrorNotice, Loading, s } from './ui';
const labels = { OPEN: 'Aguardando decisão', ACCEPTED: 'Aceita', DECLINED: 'Recusada', SUPERSEDED: 'Substituída' };
export function CaseProposals({ caseId, onChange }: { caseId: string; onChange: () => Promise<void> }) {
  const { api } = useSession();
  const [page, setPage] = useState<Page<ServiceProposal>>({ results: [], nextCursor: null });
  const [detail, setDetail] = useState<Case>();
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [now, setNow] = useState(() => Date.now());
  const [confirmed, setConfirmed] = useState<string | null>(null);
  const active = useRef(false);
  const busy = useRef(false);
  const load = useCallback(async (cursor?: string) => {
    if (busy.current) return;
    busy.current = true; setLoading(true); setError('');
    try {
      const [result, item] = await Promise.all([
        api<Page<ServiceProposal>>(`cases/${caseId}/proposals${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`),
        api<Case>(`cases/${caseId}`),
      ]);
      if (!active.current) return;
      setDetail(item); setNow(Date.now()); setConfirmed(null);
      setPage(old => ({ results: cursor ? [...old.results, ...result.results.filter(row => !old.results.some(existing => existing.id === row.id))] : result.results, nextCursor: result.nextCursor }));
    } catch (e) { if (active.current) { setError(errorMessage(e)); setDetail(undefined); } }
    finally { busy.current = false; if (active.current) setLoading(false); }
  }, [api, caseId]);
  useFocusEffect(useCallback(() => { active.current = true; void load(); return () => { active.current = false; }; }, [load]));
  async function decide(proposal: ServiceProposal, accepted: boolean) {
    if (!detail || busy.current) return;
    busy.current = true; setSending(true); setError(''); setMessage('');
    try {
      const result = await api<{ proposal: ServiceProposal; version: number }>(`cases/${caseId}/proposals/${proposal.id}/decision`, { version: detail.version, accepted });
      if (!active.current) return;
      setPage(old => ({ ...old, results: old.results.map(row => row.id === result.proposal.id ? result.proposal : row) }));
      setDetail(old => old ? { ...old, version: result.version } : old);
      setConfirmed(null); setMessage('Decisão registrada. Nenhuma cobrança foi realizada por esta ação.');
      await onChange();
    } catch (e) { if (active.current) setError(errorMessage(e)); }
    finally { busy.current = false; if (active.current) setSending(false); }
  }
  return <View style={{ gap: 14 }}>
    <Text style={s.section} accessibilityRole="header">Propostas de atendimento</Text>
    <Body>A assinatura dá acesso à plataforma. Honorários, custas, audiências e despesas são contratados separadamente.</Body>
    <Button title="Atualizar propostas" secondary disabled={sending} busy={loading} onPress={() => void load()} />
    <ErrorNotice message={error} />
    {!!message && <Body>{message}</Body>}
    {loading && <Loading />}
    {!loading && !error && !page.results.length && <Body>Nenhuma proposta apresentada neste caso.</Body>}
    {page.results.map(row => {
      const expired = Date.parse(row.validUntil) <= now;
      const canDecide = detail && !['RASCUNHO', 'RECUSADO', 'ENCERRADO'].includes(detail.state) && row.status === 'OPEN' && !expired;
      return <Card key={row.id}>
        <Text style={s.cardTitle}>Proposta {row.number} · {row.status === 'OPEN' && expired ? 'Expirada' : labels[row.status]}</Text>
        <Body>Honorários: {(row.feeCents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</Body>
        <Body>Escopo: {row.scope}</Body><Body>Despesas: {row.expenses}</Body><Body>Pagamento: {row.paymentTerms}</Body>
        <Body>Validade: {new Date(row.validUntil).toLocaleString('pt-BR')}</Body>
        {row.decidedAt && <Body>Decisão: {new Date(row.decidedAt).toLocaleString('pt-BR')}</Body>}
        {canDecide && <>
          <Body>Li o escopo, os honorários, as despesas e as condições da proposta.</Body>
          <Switch accessibilityLabel={`Confirmar leitura da proposta ${row.number}`} value={confirmed === row.id} disabled={sending || loading} onValueChange={value => setConfirmed(value ? row.id : null)} />
          <Button title={`Aceitar proposta ${row.number}`} disabled={confirmed !== row.id || loading} busy={sending} onPress={() => void decide(row, true)} />
          <Button title={`Recusar proposta ${row.number}`} secondary disabled={loading} busy={sending} onPress={() => void decide(row, false)} />
        </>}
      </Card>;
    })}
    {page.nextCursor && <Button title="Mais propostas" secondary disabled={sending} busy={loading} onPress={() => void load(page.nextCursor!)} />}
  </View>;
}
