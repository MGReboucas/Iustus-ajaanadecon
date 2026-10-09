import { useEffect, useState } from 'react';
import { errorMessage, request } from '../lib/api';
import { openPortal } from '../lib/links';
import type { BillingPlan, MobileContext } from '../lib/types';
import { Body, Button, Card, ErrorNotice, Loading, Screen, Title } from '../components/ui';
export default function Membership() {
  const [data, setData] = useState<{ plan: BillingPlan; context: MobileContext }>();
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.all([request<BillingPlan>('billing/plan'), request<MobileContext>('auth/context')]).then(([plan, context]) => { if (active) setData({ plan, context }); }).catch(e => { if (active) setError(errorMessage(e)); });
    return () => { active = false; };
  }, []);
  async function open() { setBusy(true); setError(''); try { await openPortal('/checkout'); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); } }
  return <Screen><Title>Minha associação</Title><ErrorNotice message={error} />{!data ? !error && <Loading /> : <Card>
    <Body>A associação dá acesso aos recursos da plataforma. Honorários, custas, audiências e despesas são contratados separadamente por caso.</Body>
    {data.context.checkoutAvailable && data.plan.available ? <>
      <Body>Plano anual: {(data.plan.amount / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}, em {data.plan.installments} parcelas. Confira as condições no portal antes de confirmar.</Body>
      {data.plan.sandbox && <Body>Ambiente de testes: não representa uma cobrança de produção.</Body>}
      <Button title="Continuar no portal de adesão" busy={busy} onPress={() => void open()} />
      <Body>Depois da confirmação, volte ao aplicativo. Para uma nova conta, conclua a ativação com o link recebido por e-mail.</Body>
    </> : <Body>A adesão pelo aplicativo ainda não está disponível. Se você já tem uma associação, use sua conta existente. Novos envios dependem da situação informada em Minha conta.</Body>}
  </Card>}</Screen>;
}
