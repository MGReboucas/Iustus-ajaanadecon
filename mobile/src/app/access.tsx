import { useState } from 'react';
import { router } from 'expo-router';
import { errorMessage, request } from '../lib/api';
import { readAccessLink } from '../lib/links';
import { Body, Button, ErrorNotice, Field, Screen, Title } from '../components/ui';

export default function Access() {
  const [link, setLink] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  let mode = '';
  try { mode = readAccessLink(link).mode; } catch { /* incomplete input */ }
  async function submit() {
    if (busy) return; setBusy(true); setError('');
    try {
      const action = readAccessLink(link);
      if (action.mode !== 'verify' && (password.length < 8 || password !== confirmation)) throw new Error('Use uma senha de pelo menos 8 caracteres e confirme a mesma senha.');
      await request(action.mode === 'member' ? 'billing/activate' : `auth/${action.mode}`, undefined,
        { token: action.token, ...(action.mode !== 'verify' ? { password } : {}), ...(action.mode === 'member' ? { name } : {}) });
      setLink(''); setPassword(''); setConfirmation(''); setDone(true);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <Screen><Title>Concluir meu acesso</Title>{done ? <><Body>Acesso atualizado. Entre com seu e-mail e senha.</Body><Button title="Ir para o login" onPress={() => router.replace('/sign-in')} /></> : <>
    <Body>Copie o link completo recebido por e-mail e cole abaixo para confirmar seu e-mail, ativar sua associação ou redefinir sua senha.</Body>
    <Field label="Link recebido por e-mail" value={link} onChangeText={setLink} autoCapitalize="none" autoCorrect={false} secureTextEntry editable={!busy} />
    {mode === 'member' && <Field label="Nome completo" value={name} onChangeText={setName} maxLength={150} editable={!busy} />}
    {(mode === 'reset' || mode === 'member') && <><Field label="Nova senha" value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" maxLength={128} editable={!busy} />
      <Field label="Confirmar nova senha" value={confirmation} onChangeText={setConfirmation} secureTextEntry autoCapitalize="none" maxLength={128} editable={!busy} /></>}
    <ErrorNotice message={error} /><Button title="Confirmar acesso" busy={busy} onPress={() => void submit()} />
  </>}</Screen>;
}
