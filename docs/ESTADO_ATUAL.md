# Estado atual e evidências

## Atualização de 29/09/2026 — fluxo de atendimento

Liberação administrativa de novos envios e fluxo após aceite implementados: procuração, conferência/correção, minuta interna, publicação da peça, protocolo externo com comprovante, compromissos, remarcação, movimentações e encerramento sem pendências. [Contrato, testes e limites](FLUXO_ATENDIMENTO.md). 65 testes PostgreSQL, build, migrações e quatro jornadas Edge aprovados; tela final conferida em desktop/celular. Validação local não equivale a implantação ou homologação produtiva.

## Atualização de 25/09/2026 — dashboard e comunicação

Indicadores e próximos passos por perfil, mensagens por caso, notas internas restritas ao advogado atribuído e avisos internos com leitura persistida implementados localmente. Contagens usam todo o escopo autorizado; transferência também revoga consulta a avisos antigos. 55 testes passaram no PostgreSQL, incluindo envio simultâneo com deduplicação; quatro jornadas de navegador passaram no Edge, incluindo comunicação em tela de 390px. Build do frontend aprovado e migração aplicada ao banco de desenvolvimento. [Contrato, operação e limites](DASHBOARD_COMUNICACAO.md). E-mails de novidades do caso, assinatura, pagamentos e gestão processual continuam pendentes.

## Atualização de 21/09/2026 — documentos

Documentos privados implementados localmente: upload em etapas, metadados, versões, quarentena, worker com integração ClamAV, download temporário e anexos em respostas de complemento. 47 testes no PostgreSQL, incluindo concorrência de versões. [Operação e evidências](DOCUMENTOS.md). Scanner real e armazenamento produtivo não foram homologados. Os achados financeiros abaixo permanecem abertos; o inventário de 16/09 é histórico.

> Evidências locais de 16/09/2026. Implementação e testes locais não equivalem a homologação produtiva.

A organização anterior preservou os 14 arquivos originais por SHA-256 e o histórico Git; foi publicada no commit 4b8d21f. Neste incremento, a tela de acesso foi substituída por integração TypeScript/Django, com cadastro, verificação, recuperação, sessões por portal, convites, MFA e painéis iniciais. PostgreSQL isolado do projeto está em operação local, com migrações aplicadas. O worker entrega e-mails de identidade em arquivos locais. Acesso foi publicado em e38ea41 com workflow GitHub aprovado. Casos agora têm persistência, atribuição, triagem, complemento e histórico; subdomínios reais, documentos e pagamentos integrados continuam pendentes.

## Inventário

| Componente | Evidência | Situação |
| --- | --- | --- |
| Aplicação web | [package.json](../frontend/package.json) | Next.js 15.5.25, React/React DOM 19.1.9; TypeScript incremental |
| Página pública | [app/page.js](../frontend/app/page.js) | Oferta, navegação, FAQ, preview visual de dashboard e depoimentos de exemplo |
| Layout | [app/layout.js](../frontend/app/layout.js) | Idioma pt-BR, metadados e viewport |
| Estilos | [globals.css](../frontend/app/globals.css), [home-nav.css](../frontend/app/home-nav.css), [testimonials.css](../frontend/app/testimonials.css) | CSS responsivo; fontes externas; não há relatório de acessibilidade |
| Entrada e cadastro | [acessar/page.tsx](../frontend/app/acessar/page.tsx) | Cadastro, confirmação de e-mail, sessões, recuperação e MFA integrados; login Google removido |
| Checkout | [checkout/page.js](../frontend/app/checkout/page.js), [PagBankTransparentForm.js](../frontend/app/checkout/PagBankTransparentForm.js) | Formulário, SDK, cotação e requisição ao backend; homologação não demonstrada |
| Sessão PagBank | [session/route.js](../frontend/app/api/pagbank/session/route.js) | GET interno inicia sessão externa via POST; depende de credenciais |
| Cobrança PagBank | [payment/route.js](../frontend/app/api/pagbank/payment/route.js) | POST de transação XML; validação mínima; retorna código |
| Configuração | [.env.example](../frontend/.env.example), [.gitignore](../.gitignore) | Nomes de variáveis e exclusão de arquivos locais; nenhum segredo copiado para os documentos |
| Referência estática | [index.html](../frontend/index.html) | Página HTML com Tailwind por CDN; não é a rota raiz do App Router |
| Dependências | [package-lock.json](../frontend/package-lock.json) | Lockfile existente; ausência de auditoria de vulnerabilidades nesta entrega |

Scripts da raiz incluem build, typecheck, test:e2e e verificações documentais. Django mantém identidade, auditoria e fila de e-mails no PostgreSQL. Casos possuem modelos, migração, API e interface. Demais domínios permanecem como estrutura inicial. Instalação e operação dos três processos: [Acesso local](ACESSO.md). Ambientes, banco local, venv, dependências e artefatos ficam ignorados pelo Git.

Verificação deste incremento: build e TypeScript; 35 testes no PostgreSQL, incluindo disputa por TOTP e versão de caso; quatro jornadas de navegador com Next.js 15.5.25. Apenas bancos isolados locais foram usados. Nenhum checkout, e-mail externo ou deploy foi acionado.

## Achados prioritários

| ID | Evidência e consequência | Prioridade / ação planejada |
| --- | --- | --- |
| AT-01 | `JSON.stringify({ cardToken, senderHash, installment, form })` envia todo `form`, que contém `cardNumber`, `cvv` e `expiration`, ao backend próprio | P0 antes de cobrança real: DEV-013; definir lista explícita de campos e testar ausência de cartão em payload/logs |
| AT-02 | Backend extrai `<code>` e frontend chama `onApproved`; não verifica estado financeiro antes de mostrar “Assinatura aprovada” | P0: DEV-015/016; estados pendente/pago/recusado e confirmação autoritativa |
| AT-03 | Parcela e valor de parcela vêm do navegador; backend só confere campos mínimos | P0: DEV-013/014; cotação validada e pedido imutável |
| AT-04 | Referência usa novo UUID por requisição; não há pedido persistido, webhook, sessão de cliente ou idempotência | P0: DEV-009 e DEV-014/015; timeout/retry não pode duplicar cobrança |
| AT-05 | Cadastro, sessões e recuperação implementados e testados localmente | Resolvido no incremento local; políticas, e-mail e homologação produtiva pendentes |
| AT-06 | Links de termos e privacidade apontam a âncoras sem seções correspondentes; depoimentos são modelos | Bloqueador de publicação: DEV-043 e revisão operacional |
| AT-07 | Landing anuncia 1, 6 ou 12 parcelas; formulário filtra qualquer quantidade até 12 | Decisão comercial H-05 antes de DEV-013; alinhar oferta e opções efetivas |
| AT-08 | Tratamento de XML por expressão regular, sem estratégia explícita de timeout, reconsulta e estados indeterminados | DEV-012/015 e DEV-046; confirmar contrato da API e testar erros |
| AT-09 | Casos possuem persistência e isolamento por titular/atribuição; arquivos e gestão processual pendentes | Incremento parcial; ver [Casos](CASOS.md) e não anunciar o MVP completo |

P0 significa prioridade antes de operação financeira real; não significa que um incidente já ocorreu. O levantamento não inspecionou logs de produção nem confirma exposição histórica.

## Correções documentais desta entrega

O README passou a apresentar o projeto completo e o status real. A referência divergente a Mercado Pago foi corrigida para PagBank; os comandos locais e as variáveis úteis foram mantidos. A árvore foi atualizada, e as seções originais 27–39 foram preservadas em [Diretrizes originais](DIRETRIZES_ORIGINAIS.md).

## Critério para atualizar status

Só registrar “validado” com ambiente, data, cenário, resultado e evidência. Integração PagBank requer testes de sandbox com conta habilitada. Revisão estática desta documentação não substitui teste de cobrança, teste de invasão, auditoria ou homologação.
