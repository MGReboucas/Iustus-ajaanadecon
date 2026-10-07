import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SessionProvider, useSession } from '../auth/SessionProvider';
import { colors, Loading, Screen } from '../components/ui';

function Navigation() {
  const { ready, signedIn } = useSession();
  if (!ready) return <Screen><Loading /></Screen>;
  return <Stack screenOptions={{ headerStyle: { backgroundColor: colors.background }, headerTintColor: colors.gold,
    headerTitleStyle: { color: colors.text }, contentStyle: { backgroundColor: colors.background }, headerBackTitle: 'Voltar' }}>
    <Stack.Protected guard={!signedIn}>
      <Stack.Screen name="sign-in" options={{ headerShown: false }} />
      <Stack.Screen name="recovery" options={{ title: 'Recuperar acesso' }} />
    </Stack.Protected>
    <Stack.Protected guard={signedIn}>
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="case/[id]" options={{ title: 'Meu caso' }} />
    </Stack.Protected>
  </Stack>;
}

export default function Layout() {
  return <SessionProvider><StatusBar style="light" /><Navigation /></SessionProvider>;
}
