import { router } from 'expo-router';
import { CaseDraft } from '../components/CaseDraft';
import { Body, Screen, Title } from '../components/ui';
export default function NewCase() {
  return <Screen><Title>Nova ocorrência</Title><Body>Conte o que aconteceu. Você poderá anexar documentos antes de enviar para análise.</Body>
    <CaseDraft onSaved={item => router.replace({ pathname: '/case/[id]', params: { id: item.id } })} /></Screen>;
}
