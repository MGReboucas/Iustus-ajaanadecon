import { useState } from 'react';
import { Text } from 'react-native';
import { useSession } from '../auth/SessionProvider';
import { useResource } from '../lib/useResource';
import { errorMessage } from '../lib/api';
import { openPortal } from '../lib/links';
import type { Page, PrivacyRequest } from '../lib/types';
import { Badge, Body, Button, Card, ErrorNotice, Field, Screen, Title, s } from '../components/ui';
const kinds = { ACCESS: 'Acesso aos meus dados', CORRECTION: 'Correção dos meus dados', DELETION: 'Excluir minha conta', OTHER: 'Outra solicitação' };
export default function Privacy() {
  const { api } = useSession();
  const { data, error, reload } = useResource<Page<PrivacyRequest>>('privacy/requests');
  const [kind, setKind] = useState<PrivacyRequest['kind']>('ACCESS'); const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false); const [failure, setFailure] = useState(''); const [message, setMessage] = useState('');
  const [extra, setExtra] = useState<PrivacyRequest[]>([]); const [next, setNext] = useState<string | null | undefined>();
  const cursor = next === undefined ? data?.nextCursor : next;
  async function run(action: () => Promise<void>) { if (busy) return; setBusy(true); setFailure(''); try { await action(); } catch (e) { setFailure(errorMessage(e)); } finally { setBusy(false); } }
  return <Screen><Title>Privacidade e conta</Title><Button title="Aviso de privacidade" secondary onPress={() => void run(() => openPortal('/privacidade'))} />
    <Button title="Termos do serviço" secondary onPress={() => void run(() => openPortal('/termos'))} />
    <ErrorNotice message={failure || error} retry={reload} />
    <Card>{Object.entries(kinds).map(([key, label]) => <Button key={key} title={label} secondary={kind !== key} disabled={busy} onPress={() => { setKind(key as PrivacyRequest['kind']); setMessage(''); }} />)}
      {kind === 'DELETION' && <Body>Você está solicitando a exclusão da conta. A associação responderá por este canal, incluindo eventual necessidade de retenção de registros. A solicitação não apaga imediatamente os dados.</Body>}
      <Field label="Descreva sua solicitação" value={description} onChangeText={setDescription} multiline maxLength={4000} editable={!busy} />
      <Button title={kind === 'DELETION' ? 'Confirmar solicitação de exclusão' : 'Enviar solicitação'} busy={busy} disabled={description.trim().length < 10} onPress={() => void run(async () => {
        await api('privacy/requests', { kind, description }); setDescription(''); setMessage('Solicitação registrada. Acompanhe a resposta abaixo.'); setExtra([]); setNext(undefined); await reload();
      })} />
    </Card>{!!message && <Body>{message}</Body>}
    {[...(data?.results || []), ...extra].map(row => <Card key={row.id}><Text style={s.cardTitle}>{kinds[row.kind]}</Text><Badge>{row.status === 'OPEN' ? 'Aguardando resposta' : 'Respondida'}</Badge><Body>{row.description}</Body>{!!row.response && <Body>{row.response}</Body>}</Card>)}
    {cursor && <Button title="Mais solicitações" secondary busy={busy} onPress={() => void run(async () => {
      const page = await api<Page<PrivacyRequest>>(`privacy/requests?cursor=${encodeURIComponent(cursor)}`); setExtra(old => [...old, ...page.results]); setNext(page.nextCursor);
    })} />}
  </Screen>;
}
