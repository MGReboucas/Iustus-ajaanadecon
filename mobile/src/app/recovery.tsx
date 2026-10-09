import { useState } from 'react';
import { router } from 'expo-router';
import { Body, Button, Card, ErrorNotice, Field, Label, Screen, Title } from '../components/ui';
import { errorMessage, request } from '../lib/api';

export default function Recovery() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  async function submit() {
    if (busy) return;
    if (!email.trim()) { setError('Informe seu e-mail.'); return; }
    setBusy(true); setError('');
    try { const result = await request<{ message: string }>('auth/recovery', undefined, { email: email.trim() }); setMessage(result.message); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <Screen><Label>ACESSO À SUA CONTA</Label><Title>Vamos recuperar seu acesso.</Title>
    <Body>Você receberá um link para definir uma nova senha. Você pode abri-lo no portal ou colá-lo no aplicativo em “Usar link recebido por e-mail”.</Body>
    <Card>{message ? <><Body>{message}</Body><Button title="Voltar para entrar" onPress={() => router.dismissTo('/sign-in')} /></> : <>
      <Field label="E-mail da sua conta" value={email} onChangeText={setEmail} autoCapitalize="none" autoCorrect={false} keyboardType="email-address" autoComplete="email" editable={!busy} />
      <ErrorNotice message={error} /><Button title="Enviar instruções" onPress={() => void submit()} busy={busy} />
    </>}</Card><Button title="Usar link recebido por e-mail" secondary onPress={() => router.push('/access')} />
  </Screen>;
}
