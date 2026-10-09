import { useState } from 'react';
import { Alert, Switch, Text } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../../auth/SessionProvider';
import { useResource } from '../../lib/useResource';
import type { Dashboard } from '../../lib/types';
import { Badge, Body, Button, Card, date, ErrorNotice, Field, Institution, Label, Loading, Screen, Title, s } from '../../components/ui';
import { errorMessage } from '../../lib/api';

export default function Account() {
  const { signOut, api } = useSession();
  const { data, loading, error, reload } = useResource<Dashboard>('dashboard');
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState<string | undefined>();
  const [emails, setEmails] = useState<boolean | undefined>();
  const [failure, setFailure] = useState('');
  const [message, setMessage] = useState('');
  async function save() {
    if (!data || busy) return;
    setBusy(true); setFailure(''); setMessage('');
    try {
      await api('me', { name: name ?? data.user.name, caseEmailEnabled: emails ?? data.user.caseEmailEnabled }, { method: 'PATCH' });
      await reload(); setName(undefined); setEmails(undefined); setMessage('Preferências atualizadas.');
    } catch (e) { setFailure(errorMessage(e)); } finally { setBusy(false); }
  }
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
      <Card><Field label="Nome completo" value={name ?? data.user.name} onChangeText={setName} editable={!busy} maxLength={150} />
        <Body>Receber atualizações dos casos por e-mail</Body><Switch accessibilityLabel="Receber e-mails dos casos" value={emails ?? data.user.caseEmailEnabled} onValueChange={setEmails} disabled={busy} />
        <ErrorNotice message={failure} />{!!message && <Body>{message}</Body>}<Button title="Salvar preferências" busy={busy} onPress={() => void save()} />
      </Card>
      <Card><Text style={s.cardTitle}>Associação anual</Text><Badge success={data.membership.active}>{data.membership.active ? 'Ativa' : 'Inativa'}</Badge>
        <Body>{data.membership.active ? `Válida até ${date(data.membership.expiresAt)}.` : 'Nenhuma associação ativa foi encontrada para esta conta.'}</Body>
        <Body>Seu acesso e seus casos são os mesmos no site e no aplicativo.</Body>
        <Button title="Opções da associação" secondary onPress={() => router.push('/membership')} />
      </Card>
    </>}
    <Button title="Privacidade e exclusão de conta" secondary onPress={() => router.push('/privacy')} />
    <Button title="Sair da minha conta" secondary busy={busy} onPress={() => void leave()} /><Institution />
  </Screen>;
}
