import { useState } from 'react';
import { KeyboardAvoidingView, Platform, View } from 'react-native';
import { router } from 'expo-router';
import { useSession } from '../auth/SessionProvider';
import { errorMessage } from '../lib/api';
import { Body, Brand, Button, Card, ErrorNotice, Field, Institution, Label, Screen, Title, s } from '../components/ui';

export default function SignIn() {
  const { signIn, storageError } = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit() {
    if (busy) return;
    if (!email.trim() || !password) { setError('Informe seu e-mail e sua senha.'); return; }
    setBusy(true); setError('');
    try { await signIn(email, password); setPassword(''); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <KeyboardAvoidingView style={s.fill} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <Screen><Brand /><View style={{ marginTop: 20 }}><Label>ÁREA DO ASSOCIADO</Label><Title>Seu atendimento, sempre por perto.</Title></View>
      <Body>Acompanhe seus casos e as próximas etapas com a mesma conta que você usa no site.</Body>
      <Card><Field label="E-mail" placeholder="voce@exemplo.com" autoCapitalize="none" autoCorrect={false} keyboardType="email-address" autoComplete="email" value={email} onChangeText={setEmail} editable={!busy} />
        <Field label="Senha" placeholder="Sua senha" secureTextEntry autoCapitalize="none" autoComplete="current-password" value={password} onChangeText={setPassword} editable={!busy} returnKeyType="go" onSubmitEditing={() => void submit()} />
        <ErrorNotice message={error || storageError} />
        <Button title="Entrar na minha conta" onPress={() => void submit()} busy={busy} />
        <Button title="Esqueci minha senha" secondary disabled={busy} onPress={() => router.push('/recovery')} />
      </Card>
      <Body>Se você já aderiu, conclua seu cadastro pelo link recebido por e-mail antes do primeiro acesso.</Body><Institution />
    </Screen>
  </KeyboardAvoidingView>;
}
