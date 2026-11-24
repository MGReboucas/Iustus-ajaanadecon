import { router } from 'expo-router';
import { Body, Button, Screen, Title } from '../components/ui';
export default function NotFound() {
  return <Screen><Title>Link não encontrado</Title>
    <Body>Este endereço não corresponde a uma tela do aplicativo. Abra o início para acessar sua conta e seus casos.</Body>
    <Button title="Voltar ao início" onPress={() => router.replace('/')} />
  </Screen>;
}
