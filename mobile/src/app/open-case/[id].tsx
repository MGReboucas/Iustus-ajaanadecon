import { Redirect, useLocalSearchParams } from 'expo-router';
import { useSession } from '../../auth/SessionProvider';
import SignIn from '../sign-in';
import { Body, Screen } from '../../components/ui';
export default function OpenCase() {
  const { signedIn } = useSession(); const { id } = useLocalSearchParams<{ id: string }>();
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id || '')) return <Screen><Body>Link de caso inválido.</Body></Screen>;
  return signedIn ? <Redirect href={{ pathname: '/case/[id]', params: { id } }} /> : <SignIn />;
}
