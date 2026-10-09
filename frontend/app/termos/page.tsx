import Link from 'next/link';
export const metadata = { title: 'Informações do serviço | Íustus' };
export default function Terms() {
  return <main style={{ maxWidth: 760, margin: '0 auto', padding: '64px 24px', lineHeight: 1.8 }}>
    <Link href="/">Íustus · AJA ANADECON</Link><h1>Informações do serviço</h1>
    <p>O Íustus permite cadastrar ocorrências, encaminhar documentos e acompanhar o atendimento com o advogado responsável.</p>
    <h2>Associação e contratação</h2><p>A associação remunera o acesso aos recursos da plataforma. Honorários por análise, elaboração de peças, protocolo e acompanhamento, além de custas, audiências e demais despesas, são definidos separadamente por caso. Confira o escopo, as condições e a validade da proposta antes de aceitá-la.</p>
    <p>O aceite de uma proposta no aplicativo registra a decisão; essa ação não realiza cobrança. As condições da associação são apresentadas no checkout vigente. A versão atual não implementa renovação automática.</p>
    <h2>Etapas do atendimento</h2><p>O envio de uma ocorrência depende da elegibilidade da conta e das informações exigidas. O caso passa por triagem e pode exigir complementos. O envio não garante aceite ou resultado. A procuração é assinada conforme a orientação do advogado e submetida à conferência.</p>
    <p>O advogado realiza o protocolo no sistema externo e registra as informações no atendimento. O aplicativo disponibiliza o histórico, as peças publicadas e os documentos liberados. A consulta dos casos existentes é preservada após a expiração da associação.</p>
    <h2>Condições do atendimento</h2><p>Esta página apresenta o funcionamento atual e não substitui o instrumento contratual do atendimento. Confira com o responsável o escopo, as despesas, a forma de pagamento e as condições de atuação antes de contratar.</p>
    <Link href="/privacidade">Privacidade e solicitações</Link>
  </main>;
}
