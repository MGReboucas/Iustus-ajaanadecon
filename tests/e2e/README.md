# Testes de navegador

Quatro jornadas Playwright: cadastro/verificação/login/recuperação do cliente; MFA, convite de advogado e recuperação do administrador; isolamento dos portais e CSRF; liberação administrativa, rascunho, distribuição, complemento, aceite, mensagens, notas internas, procuração, peça, protocolo, audiência e encerramento em tela pequena. Fixtures usam exclusivamente contas sintéticas e o banco iustus_e2e. Traces e screenshots automáticos ficam desativados para não persistir fatores e tokens. `IUSTUS_DASHBOARD_SCREENSHOT` permite capturar somente o painel sintético final, após autenticação, para revisão visual.

Preparar o banco, compilar o frontend e executar npm run test:e2e pela raiz. O runner inicia e encerra seus servidores; portas 3000/8000 precisam estar livres. No Windows local, PLAYWRIGHT_CHANNEL=msedge usa o Edge instalado; CI instala Chromium. [Comandos completos](../../docs/ACESSO.md) · [Plano dos demais testes](../../docs/TESTES.md).

A jornada jurídica também cadastra modelo revisado, gera/baixa procuração PDF e verifica o ZIP exportado, inclusive ausência da nota interna. Capturas sintéticas de conferência ficam em `.local/`.
