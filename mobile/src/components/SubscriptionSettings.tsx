import { useState } from 'react';
import { Switch } from 'react-native';
import { useSession } from '../auth/SessionProvider';
import { useResource } from '../lib/useResource';
import { errorMessage } from '../lib/api';
import type { SubscriptionState } from '../../../contracts/api';
import { Body, Button, Card, ErrorNotice, Title } from './ui';

export default function SubscriptionSettings() {
  const { api } = useSession();
  const { data, error, reload } = useResource<SubscriptionState>('billing/subscription');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  async function cancel() {
    if (!confirmed || busy) return;
    setBusy(true); setFailure('');
    try { await api('billing/subscription', { cancelRenewal: true }); await reload(); }
    catch (e) { setFailure(errorMessage(e)); }
    finally { setBusy(false); }
  }
  const sub = data?.subscription;
  return <Card><Title>Renovação da associação</Title><ErrorNotice message={error || failure} retry={reload} />
    {sub ? <><Body>{sub.automaticRenewal ? 'Renovação automática ativa' : sub.canceledAt ? 'Próxima renovação cancelada' : 'Renovação em conferência'}</Body>
      <Body>Plano anual: {(sub.amount / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}, em {sub.installments} parcelas.</Body>
      {sub.nextChargeAt && <Body>Próxima cobrança: {new Date(sub.nextChargeAt).toLocaleDateString('pt-BR')}.</Body>}
      {!sub.canceledAt && <><Body>Quero cancelar a próxima renovação automática.</Body><Switch accessibilityLabel="Confirmar cancelamento da renovação" value={confirmed} onValueChange={setConfirmed} disabled={busy} /><Button title="Cancelar próxima renovação" disabled={!confirmed} busy={busy} onPress={() => void cancel()} /></>}
      <Body>A vigência já paga e os casos existentes são preservados. Uma cobrança já iniciada precisa de atendimento para eventual estorno.</Body></> : data && <Body>Não há renovação automática cadastrada.</Body>}
  </Card>;
}
