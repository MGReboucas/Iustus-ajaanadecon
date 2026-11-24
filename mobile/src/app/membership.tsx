import { useSession } from '../auth/SessionProvider';
import SubscriptionSettings from '../components/SubscriptionSettings';
import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { AppState } from 'react-native';
import { errorMessage, request } from '../lib/api';
import { openPortal } from '../lib/links';
import type { BillingPlan, MobileContext } from '../lib/types';
import { Body, Button, Card, ErrorNotice, Loading, Screen, Title } from '../components/ui';
export default function Membership() {
  const { signedIn } = useSession();
  const [data, setData] = useState<{ plan: BillingPlan; context: MobileContext }>();
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const load = useCallback(async () => {
      const run = ++generation.current; setError('');
      try {
        const [plan, context] = await Promise.all([request<BillingPlan>('billing/plan'), request<MobileContext>('auth/context')]);
        if (run === generation.current) setData({ plan, context });
      } catch (e) { if (run === generation.current) { setData(undefined); setError(errorMessage(e)); } }
  }, []);
  useFocusEffect(useCallback(() => {
    void load();
    const subscription = AppState.addEventListener('change', state => { if (state === 'active') void load(); });
    return () => { generation.current++; subscription.remove(); };
  }, [load]));
  async function open() { setBusy(true); setError(''); try { await openPortal('/checkout'); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); } }
  return <Screen><Title>Minha associação</Title><ErrorNotice message={error} retry={() => void load()} />{!data ? !error && <Loading /> : <Card>
    <Body>A associação dá acesso aos recursos da plataforma. Honorários, custas, audiências e despesas são contratados separadamente por caso.</Body>
    {data.context.checkoutAvailable && data.plan.available ? <>
      <Body>Plano anual: {(data.plan.amount / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}, em {data.plan.installments} parcelas. Vigência de um ano, sem renovação automática. Para renovar, faça uma nova compra.</Body>
      {data.plan.sandbox && <Body>Ambiente de testes: não representa uma cobrança de produção.</Body>}
      <Button title="Pagar com Mercado Pago no portal" busy={busy} onPress={() => void open()} />
      <Body>Depois da confirmação, volte ao aplicativo. Para uma nova conta, conclua a ativação com o link recebido por e-mail.</Body>
    </> : <Body>A adesão pelo aplicativo ainda não está disponível. Se você já tem uma associação, use sua conta existente. Novos envios dependem da situação informada em Minha conta.</Body>}
  </Card>}{signedIn && <SubscriptionSettings />}</Screen>;
}
