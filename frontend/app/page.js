'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import Brand from '@/components/Brand';
import './testimonials.css';
import './home-nav.css';
import './pricing.css';
import './institutional.css';

function Mark({ small = false }) {
  return <Brand size={small ? 48 : 96} decorative />;
}

const Arrow = () => <span className="arrow" aria-hidden="true">→</span>;

const Check = () => <span className="check" aria-hidden="true">✓</span>;

function AssociationLogo() {
  return <Image className="association-logo" src="/brand/Aja%20anadecon.png" alt="AJA ANADECON — A voz do consumidor" width={1024} height={1024} sizes="88px" />;
}

function Logo() {
  return <a className="logo" href="#inicio" aria-label="Íustus, início"><Brand decorative /></a>;
}

export default function Home() {
  const [open, setOpen] = useState(false);
  const closeMenu = () => setOpen(false);

  return (
    <main id="inicio">
      <header className="nav-wrap">
        <nav className="nav container" aria-label="Navegação principal">
          <Logo />
          <button className="menu-button" onClick={() => setOpen(!open)} aria-label="Abrir menu" aria-expanded={open}>
            <span></span><span></span><span></span>
          </button>
          <div className={`nav-links ${open ? 'is-open' : ''}`}>
            <a href="#como-funciona" onClick={closeMenu}>Como funciona</a>
            <a href="#beneficios" onClick={closeMenu}>Benefícios</a>
            <a href="#plano" onClick={closeMenu}>Plano</a>
            <Link className="account-cta" href="/acessar" onClick={closeMenu}>Área do associado</Link>
            <Link className="nav-cta" href="/checkout" onClick={closeMenu}>Associar-me <Arrow /></Link>
          </div>
        </nav>
      </header>

      <section className="hero container">
        <div className="hero-copy">
          <p className="institutional-credit"><AssociationLogo /><span>ÍUSTUS · Um projeto da<br /><strong>AJA ANADECON</strong></span></p>
          <div className="eyebrow"><span className="pulse"></span> Atendimento online, do seu lado</div>
          <h1>Quando a vida exige uma defesa, <span>você não precisa enfrentar sozinho.</span></h1>
          <p className="hero-text">Associe-se à Iustus, relate o que aconteceu e envie seus documentos. Nossos advogados analisam cada caso; após o aceite, você assina a procuração específica e acompanha o atendimento pelo painel.</p>
          <div className="hero-actions">
            <Link className="button primary" href="/checkout">Associe-se por 12x de R$ 79,90 <Arrow /></Link>
            <a className="button ghost" href="#como-funciona">Entenda como funciona <span className="play">▶</span></a>
          </div>
          <ul className="hero-assurances" aria-label="Destaques da associação"><li>Uso ilimitado</li><li>12x de R$ 79,90</li><li>Dashboard seguro</li></ul>
          <div className="hero-proof">
            <div className="avatars"><i>AM</i><i>RC</i><i>LF</i><i>+</i></div>
            <p><strong>Atendimento digital e seguro</strong><br />para você resolver sem sair de casa.</p>
          </div>
        </div>
        <div className="hero-visual" aria-label="Prévia da plataforma Íustus">
          <div className="orbit orbit-one"></div><div className="orbit orbit-two"></div>
          <div className="case-window">
            <div className="window-top"><div className="window-brand"><Mark small /> <b>MEU PAINEL</b></div><span>•••</span></div>
            <div className="workspace">
              <aside><span className="active-icon">⌂</span><span>▤</span><span>◌</span><span>◴</span></aside>
              <div className="case-content">
                <div className="case-heading"><div><small>MEUS CASOS</small><h3>Sua defesa em um só lugar</h3></div><button>+ Nova ocorrência</button></div>
                <div className="case-card"><div className="case-icon">⚖</div><div><b>Defesa administrativa</b><p>Documentos e procuração recebidos</p></div><span className="status">Em andamento</span></div>
                <div className="timeline"><p><i></i><span><b>Procuração validada</b><small>Agora mesmo</small></span></p><p><i></i><span><b>Defesa sendo preparada</b><small>Atualizações pelo painel</small></span></p><p><i></i><span><b>Defesa disponível no painel</b><small>Pronta para você acessar</small></span></p></div>
              </div>
            </div>
          </div>
          <div className="floating security"><span>⌁</span><div><b>Seus dados protegidos</b><small>Ambiente criptografado</small></div></div>
          <div className="floating lawyer"><div className="lawyer-avatar">⚖</div><div><b>Especialista designado</b><small>Jornada acompanhada</small></div><Check /></div>
        </div>
      </section>

      <section className="trust-bar"><div className="container trust-inner"><span>ACOMPANHAMENTO QUANDO VOCÊ PRECISAR</span><div><b>100%</b><small>digital</small></div><i></i><div><b>1 associação</b><small>por ano</small></div><i></i><div><b>Uso ilimitado</b><small>durante a vigência</small></div></div></section>

      <section id="como-funciona" className="section container how">
        <div className="section-intro"><div className="eyebrow">SIMPLICIDADE EM CADA ETAPA</div><h2>Da preocupação à defesa,<br /><span>em três passos.</span></h2></div>
        <div className="steps">
          <article><span className="step-number">01</span><div className="step-icon">◈</div><h3>Associe-se à ÍUSTUS</h3><p>Após o pagamento da adesão anual, receba por e-mail o link para concluir seu cadastro e entrar no painel.</p></article>
          <article><span className="step-number">02</span><div className="step-icon">↥</div><h3>Conte o que aconteceu</h3><p>Cadastre sua ocorrência com a descrição do fato, a data e os documentos comprobatórios. Um advogado receberá o caso para análise.</p></article>
          <article><span className="step-number">03</span><div className="step-icon">✓</div><h3>Acompanhe cada etapa</h3><p>Se o caso for aprovado, a associação envia a procuração específica para você assinar. Acompanhe o andamento no painel e receba avisos por e-mail.</p></article>
        </div>
      </section>

      <section id="beneficios" className="benefits"><div className="container benefits-grid"><div className="benefit-copy"><div className="eyebrow">NÃO É APENAS UMA PLATAFORMA</div><h2>É a tranquilidade de ter <span>uma defesa ao seu alcance.</span></h2><p>A adesão anual permite cadastrar ocorrências durante a vigência. Cada pedido é analisado individualmente pelo advogado, que poderá aceitar, solicitar informações ou justificar a recusa.</p><a href="#plano" className="text-link">Conheça a associação ÍUSTUS <Arrow /></a></div><div className="benefit-list"><article><span>01</span><div><h3>Uso ilimitado durante o ano</h3><p>Envie quantos casos precisar enquanto sua associação estiver vigente.</p></div></article><article><span>02</span><div><h3>Caso, documentos e procuração no mesmo painel</h3><p>Envie documentos com a ocorrência e assine a procuração de cada caso somente após o aceite.</p></div></article><article><span>03</span><div><h3>Sua defesa preparada e acessível</h3><p>Consulte o andamento, as pendências e os documentos do seu atendimento pelo painel.</p></div></article></div></div></section>

      <section id="plano" className="section pricing container">
        <div className="pricing-intro"><div className="eyebrow">ASSOCIAÇÃO ANUAL</div><h2>Defesas quando precisar,<br />em um único plano.</h2><p>Associe-se uma vez ao ano e use a plataforma quantas vezes precisar durante a vigência da sua associação.</p></div>
        <article className="price-card"><div className="price-top"><div><span className="plan-label">PLANO ÍUSTUS ANUAL</span><h3>Atendimento disponível o ano todo.</h3></div><span className="best">USO ILIMITADO</span></div><div className="price price-installments"><span className="installment-count">12x de</span><strong>R$ 79,90</strong></div><p className="price-equivalent">Associação anual · 12 parcelas de R$ 79,90. Total de R$ 958,80.</p><ul><li><Check /> Uso ilimitado da plataforma durante a associação</li><li><Check /> Envio de ocorrências e documentos online</li><li><Check /> Acompanhamento de cada solicitação pelo painel</li><li><Check /> Procuração por caso e acompanhamento jurídico</li></ul><Link className="button primary price-button" href="/checkout">Quero me associar à ÍUSTUS <Arrow /></Link><small className="secure-line">⌁ Pagamento seguro · 12x de R$ 79,90</small></article>
      </section>

      <section className="faq container"><div><div className="eyebrow">DÚVIDAS FREQUENTES</div><h2>Clareza antes<br />de começar.</h2></div><div className="faq-list"><details><summary>A quem pertence o projeto Íustus?<span>+</span></summary><p>A Íustus é um projeto que pertence à AJA ANADECON. A plataforma permite cadastrar ocorrências e acompanhar o atendimento jurídico online.</p></details><details open><summary>Posso usar a plataforma mais de uma vez?<span>+</span></summary><p>Sim. Sua associação dá acesso ilimitado à plataforma durante o período anual de vigência.</p></details><details><summary>Como funciona o pagamento?<span>+</span></summary><p>A associação anual é paga em 12 parcelas de R$ 79,90, totalizando R$ 958,80, com acesso à plataforma durante o período anual de vigência.</p></details><details><summary>O que preciso enviar para iniciar um caso?<span>+</span></summary><p>Envie a descrição do fato, a data do ocorrido e os documentos comprobatórios. A procuração é enviada pela associação somente depois que o advogado aprovar o caso, e vale para aquele caso específico.</p></details><details><summary>Como acompanho meu caso?<span>+</span></summary><p>O painel mostra o gráfico das solicitações, o andamento e as pendências de cada caso. Você também recebe avisos por e-mail quando houver novidades no atendimento.</p></details></div></section>

      <section className="final-cta"><div className="cta-light"></div><div className="container cta-content"><Mark /><div><div className="eyebrow">SEU PRÓXIMO PASSO COMEÇA AQUI</div><h2>Associe-se e acompanhe<br /><span>sempre que precisar.</span></h2></div><Link className="button primary" href="/checkout">Associar-me por 12x de R$ 79,90 <Arrow /></Link></div></section>

      <footer><div className="container footer-inner"><Logo /><p className="institutional-credit footer-credit"><AssociationLogo /><span>© 2026 ÍUSTUS. Um projeto da <strong>AJA ANADECON</strong>.<br />Atendimento online, com clareza e segurança.</span></p><div><a href="#privacidade">Privacidade</a><a href="#termos">Termos de uso</a></div></div></footer>
      <div className="mobile-purchase"><div><small>Plano anual</small><b>12x de R$ 79,90</b></div><Link href="/checkout">Associar-me <Arrow /></Link></div>
    </main>
  );
}
