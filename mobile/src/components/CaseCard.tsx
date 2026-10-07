import { Pressable, Text, View } from 'react-native';
import { router } from 'expo-router';
import Ionicons from '@expo/vector-icons/Ionicons';
import type { Case } from '../lib/types';
import { Badge, colors, s } from './ui';

export function CaseCard({ item }: { item: Case }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={`Abrir ${item.title || 'caso'}: ${item.stateLabel}`} onPress={() => router.push({ pathname: '/case/[id]', params: { id: item.id } })} style={({ pressed }) => [s.card, pressed && { opacity: .7 }]}>
    <View style={s.row}><Text style={[s.caption, s.grow]}>CASO #{item.reference}</Text><Ionicons name="chevron-forward" color={colors.gold} size={18} /></View>
    <Text style={s.cardTitle}>{item.title || 'Rascunho sem título'}</Text><Text style={s.caption}>{item.categoryLabel || 'Categoria ainda não definida'}</Text><Badge>{item.stateLabel}</Badge>
  </Pressable>;
}
