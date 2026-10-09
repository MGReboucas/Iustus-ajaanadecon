import Link from 'next/link';
export const metadata = { title: 'Privacidade | Íustus' };
export default function Privacy() {
  return <main style={{ maxWidth: 760, margin: '0 auto', padding: '64px 24px', lineHeight: 1.8 }}>
    <Link href="/">Íustus · AJA ANADECON</Link><h1>Privacidade</h1>
    <p>O Íustus utiliza os dados de cadastro para identificar sua conta e controlar o acesso. Relatos, documentos e mensagens são utilizados para a análise e o acompanhamento dos seus atendimentos.</p>
    <h2>Acesso aos seus casos</h2><p>Você consulta seus próprios casos. O advogado responsável acessa os atendimentos atribuídos a ele. Notas e minutas internas não são apresentadas ao associado. Operações de segurança e atendimento são registradas para rastreabilidade.</p>
    <h2>Documentos e comunicações</h2><p>Os arquivos passam por validação e verificação antes de serem liberados. Os e-mails avisam sobre atualizações e direcionam ao ambiente autenticado. Você pode ajustar o recebimento de e-mails em Minha conta.</p>
    <h2>Solicitações sobre dados</h2><p>No aplicativo, abra Minha conta → Privacidade e exclusão de conta. É possível solicitar acesso, correção, exclusão ou registrar outra solicitação e acompanhar a resposta. Pedidos de exclusão são analisados; o registro do pedido não significa eliminação imediata de todos os documentos.</p>
    <h2>Sobre esta página</h2><p>Estas informações descrevem o uso dos dados no aplicativo. Para esclarecer o tratamento dos seus registros, envie uma solicitação na área de privacidade da sua conta.</p>
    <Link href="/termos">Informações do serviço</Link>
  </main>;
}
