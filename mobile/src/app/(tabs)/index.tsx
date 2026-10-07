import { RefreshControl, StyleSheet, Text, View } from 'react-native';
import { router } from 'expo-router';
import Ionicons from '@expo/vector-icons/Ionicons';
import { useResource } from '../../lib/useResource';
import type { Dashboard } from '../../lib/types';
import { Badge, Body, Brand, Button, Card, colors, date, Empty, ErrorNotice, Label, Loading, Screen, Title, s } from '../../components/ui';
import { CaseCard } from '../../components/CaseCard';

export default function Home() {
  const { data, error, loading, reload } = useResource<Dashboard>('dashboard');
  return <Screen refreshControl={<RefreshControl refreshing={loading && !!data} onRefresh={reload} tintColor={colors.gold} />}>
    <Brand compact /><ErrorNotice message={error} retry={reload} />
    {!data ? (loading ? <Loading /> : null) : <>
      <View><Label>SEU PAINEL</Label><Title>Olá, {data.user.name.split(' ')[0] || 'associado'}.</Title><Body>Vamos acompanhar o seu atendimento?</Body></View>
      <Card><View style={s.row}><Ionicons name="shield-checkmark-outline" color={colors.gold} size={24} /><Text style={s.cardTitle}>Sua associação</Text></View>
        <Badge success={data.membership.active}>{data.membership.active ? 'Associação ativa' : 'Associação inativa'}</Badge>
        <Body>{data.membership.active ? `Vigência até ${date(data.membership.expiresAt)}. Seus atendimentos em um só lugar.` : 'Você pode acompanhar seus casos anteriores. Novos envios dependem de uma associação ativa.'}</Body>
      </Card>
      <View style={styles.metrics}><View style={[s.card, styles.metric]}><Text style={styles.number}>{data.totalCases}</Text><Text style={s.caption}>Casos cadastrados</Text></View><View style={[s.card, styles.metric]}><Text style={styles.number}>{data.attentionCount}</Text><Text style={s.caption}>Precisam de atenção</Text></View></View>
      <Text style={s.section} accessibilityRole="header">Sua próxima etapa</Text>
      {data.attentionCases.length ? data.attentionCases.map(item => <CaseCard key={item.id} item={item} />) : <Empty title="Tudo acompanhado" message="Não há casos precisando da sua atenção neste momento." />}
      <Button title="Ver todos os meus casos" onPress={() => router.navigate('/cases')} />
      {!!data.recentActivity.length && <><Text style={s.section} accessibilityRole="header">Últimas movimentações</Text>{data.recentActivity.map(item => <Card key={item.id}>
        <Text style={s.caption}>{date(item.createdAt)} · #{item.reference}</Text><Text style={s.cardTitle}>{item.title}</Text><Body>{item.stateLabel}</Body><Button secondary title="Acompanhar caso" onPress={() => router.push({ pathname: '/case/[id]', params: { id: item.caseId } })} />
      </Card>)}</>}
    </>}
  </Screen>;
}
const styles = StyleSheet.create({ metrics: { flexDirection: 'row', gap: 12 }, metric: { flex: 1, padding: 16 }, number: { color: colors.gold, fontSize: 32, fontWeight: '700' } });
