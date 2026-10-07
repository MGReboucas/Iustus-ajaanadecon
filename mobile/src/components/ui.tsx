import { PropsWithChildren } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, ScrollViewProps, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@expo/vector-icons/Ionicons';

export const colors = { background: '#070e1b', card: '#111e32', line: '#26364e', text: '#f2f4f8', muted: '#a8b5c9', gold: '#e5b869', success: '#97dfbf', error: '#ffb1ae' };

export function Screen({ children, ...props }: PropsWithChildren<ScrollViewProps>) {
  return <SafeAreaView style={s.fill} edges={['top', 'left', 'right']}><ScrollView contentContainerStyle={s.page} keyboardShouldPersistTaps="handled" {...props}>{children}</ScrollView></SafeAreaView>;
}
export function Brand({ compact = false }: { compact?: boolean }) {
  return <View style={s.brand}><Image source={require('../../assets/iustus.png')} style={{ width: compact ? 52 : 78, height: compact ? 52 : 78 }} accessibilityLabel="Íustus" /><View><Text style={s.brandName}>ÍUSTUS</Text><Text style={s.caption}>Sua defesa, ao seu alcance.</Text></View></View>;
}
export function Institution() {
  return <View style={s.institution}><Image source={require('../../assets/aja-anadecon.png')} style={s.association} accessibilityLabel="AJA ANADECON" /><View style={s.grow}><Text style={s.caption}>Um projeto da</Text><Text style={s.institutionName}>AJA ANADECON</Text></View></View>;
}
export function Title({ children }: PropsWithChildren) { return <Text style={s.title} accessibilityRole="header">{children}</Text>; }
export function Label({ children }: PropsWithChildren) { return <Text style={s.label}>{children}</Text>; }
export function Body({ children }: PropsWithChildren) { return <Text style={s.body}>{children}</Text>; }
export function Card({ children }: PropsWithChildren) { return <View style={s.card}>{children}</View>; }
export function Button({ title, onPress, busy = false, secondary = false, disabled = false }: { title: string; onPress: () => void; busy?: boolean; secondary?: boolean; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled: busy || disabled, busy }} onPress={onPress} disabled={busy || disabled}
    style={({ pressed }) => [s.button, secondary && s.secondary, (busy || disabled || pressed) && { opacity: .65 }]}>
    {busy ? <ActivityIndicator color={secondary ? colors.gold : colors.background} /> : <Text style={[s.buttonText, secondary && { color: colors.gold }]}>{title}</Text>}
  </Pressable>;
}
export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return <View style={s.field}><Text style={s.fieldLabel}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor="#8191aa" selectionColor={colors.gold} style={s.input} {...props} /></View>;
}
export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  if (!message) return null;
  return <View style={s.error}><Text accessibilityRole="alert" style={s.errorText}>{message}</Text>{retry && <Button title="Tentar novamente" onPress={retry} secondary />}</View>;
}
export function Loading() { return <View style={s.loading}><ActivityIndicator color={colors.gold} size="large" accessibilityLabel="Carregando" /><Body>Carregando seu atendimento…</Body></View>; }
export function Empty({ title, message }: { title: string; message: string }) {
  return <Card><Ionicons name="folder-open-outline" size={30} color={colors.gold} /><Text style={s.cardTitle}>{title}</Text><Body>{message}</Body></Card>;
}
export function Badge({ children, success = false }: PropsWithChildren<{ success?: boolean }>) {
  return <View style={[s.badge, success && { backgroundColor: '#19362f' }]}><Text style={[s.badgeText, success && { color: colors.success }]}>{children}</Text></View>;
}
export function date(value?: string | null) { return value ? new Date(value.length === 10 ? value + 'T12:00:00' : value).toLocaleDateString('pt-BR') : '—'; }

export const s = StyleSheet.create({
  fill: { flex: 1, backgroundColor: colors.background }, page: { padding: 24, paddingBottom: 40, gap: 20, width: '100%', maxWidth: 720, alignSelf: 'center', flexGrow: 1 },
  brand: { flexDirection: 'row', gap: 14, alignItems: 'center' }, brandName: { color: colors.gold, fontSize: 24, letterSpacing: 4, fontWeight: '700' },
  caption: { color: colors.muted, fontSize: 12, lineHeight: 19 }, grow: { flex: 1 },
  institution: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingTop: 16, borderTopWidth: 1, borderTopColor: colors.line },
  association: { width: 54, height: 54, backgroundColor: '#fff', borderRadius: 10, resizeMode: 'contain' }, institutionName: { fontSize: 13, color: colors.text, fontWeight: '600' },
  title: { fontSize: 32, lineHeight: 39, color: colors.text, fontWeight: '700', letterSpacing: -.7 }, label: { fontSize: 11, letterSpacing: 2, fontWeight: '700', color: colors.gold, marginBottom: 8 },
  body: { color: colors.muted, fontSize: 15, lineHeight: 23 }, card: { padding: 20, borderRadius: 18, gap: 12, borderWidth: 1, borderColor: colors.line, backgroundColor: colors.card },
  cardTitle: { color: colors.text, fontSize: 18, fontWeight: '600', lineHeight: 25 }, button: { backgroundColor: colors.gold, minHeight: 50, borderRadius: 12, alignItems: 'center', justifyContent: 'center', padding: 14 },
  buttonText: { color: colors.background, fontWeight: '700', fontSize: 15, textAlign: 'center' }, secondary: { backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.line },
  field: { gap: 8 }, fieldLabel: { color: colors.text, fontSize: 13, fontWeight: '600' }, input: { backgroundColor: colors.background, borderWidth: 1, borderColor: colors.line, borderRadius: 12, minHeight: 52, padding: 14, color: colors.text, fontSize: 16 },
  error: { padding: 16, gap: 12, borderWidth: 1, borderColor: '#643939', backgroundColor: '#2c1c27', borderRadius: 12 }, errorText: { color: colors.error, fontSize: 14, lineHeight: 21 },
  loading: { paddingVertical: 48, alignItems: 'center', gap: 18 }, badge: { backgroundColor: '#352c22', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, alignSelf: 'flex-start' }, badgeText: { color: colors.gold, fontSize: 12, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 }, section: { color: colors.text, fontSize: 20, fontWeight: '600' },
});
