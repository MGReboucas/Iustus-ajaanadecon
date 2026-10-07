import { useState } from 'react';
import { Alert, Text } from 'react-native';
import { useSession } from '../../auth/SessionProvider';
import { useResource } from '../../lib/useResource';
import type { Dashboard } from '../../lib/types';
import { Badge, Body, Button, Card, date, ErrorNotice, Institution, Label, Loading, Screen, Title, s } from '../../components/ui';
import { errorMessage } from '../../lib/api';

export default function Account() {
  const { signOut } = useSession();
  const { data, loading, error, reload } = useResource<Dashboard>('dashboard');
  const [busy, setBusy] = useState(false);
  async function leave() {
    if (busy) return;
    setBusy(true);
    try { await signOut(); }
    catch (err) { Alert.alert('Saída da conta', errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <Screen><Label>SEU ACESSO</Label><Title>Minha conta</Title><ErrorNotice message={error} retry={reload} />
    {!data ? (loading ? <Loading /> : null) : <>
      <Card><Text style={s.cardTitle}>{data.user.name}</Text><Body>{data.user.email}</Body><Badge>Associado</Badge></Card>
      <Card><Text style={s.cardTitle}>Associação anual</Text><Badge success={data.membership.active}>{data.membership.active ? 'Ativa' : 'Inativa'}</Badge>
        <Body>{data.membership.active ? `Válida até ${date(data.membership.expiresAt)}.` : 'Nenhuma associação ativa foi encontrada para esta conta.'}</Body>
        <Body>Seu acesso e seus casos são os mesmos no site e no aplicativo.</Body>
      </Card>
    </>}
    <Button title="Sair da minha conta" secondary busy={busy} onPress={() => void leave()} /><Institution />
  </Screen>;
}
