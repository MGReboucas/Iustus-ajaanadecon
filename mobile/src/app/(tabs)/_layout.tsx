import { Tabs } from 'expo-router';
import Ionicons from '@expo/vector-icons/Ionicons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '../../components/ui';

export default function TabsLayout() {
  const bottom = Math.max(useSafeAreaInsets().bottom, 12);
  return <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: colors.gold, tabBarInactiveTintColor: colors.muted,
    tabBarStyle: { backgroundColor: colors.background, borderTopColor: colors.line, height: 58 + bottom, paddingTop: 8, paddingBottom: bottom }, tabBarLabelStyle: { fontSize: 12, lineHeight: 16 } }}>
    <Tabs.Screen name="index" options={{ title: 'Início', tabBarIcon: ({ color, size }) => <Ionicons name="grid-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="cases" options={{ title: 'Meus casos', tabBarIcon: ({ color, size }) => <Ionicons name="folder-open-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="account" options={{ title: 'Minha conta', tabBarIcon: ({ color, size }) => <Ionicons name="person-circle-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="notifications" options={{ title: 'Avisos', tabBarIcon: ({ color, size }) => <Ionicons name="notifications-outline" color={color} size={size} /> }} />
  </Tabs>;
}
