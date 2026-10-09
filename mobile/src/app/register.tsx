import { useEffect, useState } from 'react';
import { Switch } from 'react-native';
import { router } from 'expo-router';
import { errorMessage, request } from '../lib/api';
import { openPortal } from '../lib/links';
import type { MobileContext } from '../lib/types';
import { Body, Button, Card, ErrorNotice, Field, Loading, Screen, Title } from '../components/ui';

export default function Register() {
  const [context, setContext] = useState<MobileContext>();
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [accepted, setAccepted] = useState(false); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [message, setMessage] = useState('');
  async function load() { try { setContext(await request<MobileContext>('auth/context')); setError(''); } catch (e) { setError(errorMessage(e)); } }
  useEffect(() => {
    let active = true;
    request<MobileContext>('auth/context').then(value => { if (active) setContext(value); }).catch(e => { if (active) setError(errorMessage(e)); });
    return () => { active = false; };
  }, []);
  async function run(action: () => Promise<void>) {
    if (busy) return; setBusy(true); setError('');
    try { await action(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <Screen><Title>Primeiro acesso</Title><ErrorNotice message={error} retry={() => void load()} />{!context ? <Loading /> : <>
    {context.registrationAvailable ? <Card><Field label="Nome completo" value={name} onChangeText={setName} maxLength={150} editable={!busy} />
      <Field label="E-mail de cadastro" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" editable={!busy} />
      <Field label="Criar senha" value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" maxLength={128} editable={!busy} />
      <Button title="Ler privacidade" secondary onPress={() => void run(() => openPortal('/privacidade'))} />
      <Button title="Ler termos" secondary onPress={() => void run(() => openPortal('/termos'))} />
      <Body>Li os termos e o aviso de privacidade vigentes.</Body><Switch accessibilityLabel="Aceitar termos e privacidade" value={accepted} onValueChange={setAccepted} disabled={busy} />
      <Button title="Criar minha conta" disabled={!accepted || name.trim().length < 2 || !email.trim() || password.length < 8} busy={busy} onPress={() => void run(async () => {
        const result = await request<{ message: string }>('auth/register', undefined, { name, email: email.trim(), password, policyVersion: context.policyVersion });
        setPassword(''); setMessage(result.message);
      })} />
      <Button title="Reenviar confirmação de e-mail" secondary disabled={!email.trim()} busy={busy} onPress={() => void run(async () => {
        const result = await request<{ message: string }>('auth/resend', undefined, { email: email.trim() }); setMessage(result.message);
      })} />
    </Card> : <><Body>O acesso é ativado após a confirmação da associação. Se você já aderiu, use o link recebido por e-mail.</Body>
      {context.checkoutAvailable && context.billingAvailable && <Button title="Continuar adesão no portal" busy={busy} onPress={() => void run(() => openPortal('/checkout'))} />}
      <Field label="E-mail da associação" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" editable={!busy} />
      <Button title="Reenviar link de ativação" busy={busy} disabled={!email.trim()} onPress={() => void run(async () => {
        const result = await request<{ message: string }>('billing/resend', undefined, { email: email.trim() }); setMessage(result.message);
      })} />
    </>}
    {!!message && <Body>{message}</Body>}
    <Button title="Já tenho o link do e-mail" secondary onPress={() => router.push('/access')} />
    <Button title="Informações da associação" secondary onPress={() => router.push('/membership')} />
  </>}</Screen>;
}
