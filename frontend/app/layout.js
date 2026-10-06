import './globals.css';
import '@/components/brand.css';

export const metadata = {
  title: {
    default: 'ÍUSTUS | Atendimento online, sem complicação',
    template: '%s | ÍUSTUS',
  },
  description: 'Associe-se à Iustus por 12x de R$ 79,90. Cadastre ocorrências, assine a procuração dos casos aprovados e acompanhe o atendimento online.',
  keywords: ['assinatura jurídica', 'dashboard jurídico', 'procuração online'],
  openGraph: {
    title: 'ÍUSTUS | Atendimento online por assinatura',
    description: 'Envie seus casos, documentos e procuração. Acompanhe tudo em um só dashboard.',
    locale: 'pt_BR',
    type: 'website',
  },
  icons: { icon: [{ url: '/brand/iustus-logo.svg', type: 'image/svg+xml' }], apple: '/brand/iustus-touch.png' },
  robots: { index: true, follow: true },
};

export const viewport = { themeColor: '#070c18' };

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
