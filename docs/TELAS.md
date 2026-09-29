# Telas e comportamento de interface

> Rotas futuras são propostas. Padrão visual a preservar: azul-marinho, dourado e tipografia da identidade Iustus, com contraste e legibilidade verificados.

As telas futuras serão Next.js + TypeScript, consumindo a API Django na mesma origem do respectivo portal. Os caminhos abaixo são relativos ao host: apresentação no site público; checkout, assinatura e `/cliente` no portal do cliente; `/advogado` e `/admin` no portal profissional. Acesso, recuperação, perfil e avisos respeitam o portal corrente e sua sessão. O site público direciona a autenticação ao portal correspondente. Rotas profissionais no host do cliente são negadas; ocultar o menu não é autorização. `/admin` é o dashboard da aplicação, não o Django Admin. A equipe completa MFA antes de acessar o painel.

| ID | Rota / tela | Situação atual | Conteúdo e ações do MVP | Requisitos |
| --- | --- | --- | --- | --- |
| UI-01 | `/` | Implementada em código | Proposta aprovada, plano, FAQ, termos e acesso; remover exemplos de depoimento antes de publicar | RF-001/037 |
| UI-02 | `/acessar` | Integrada ao Django; testes locais | Cadastro, login, verificação, erros seguros e logout; Google removido do incremento | RF-002/003/005 |
| UI-03 | `/recuperar`, `/redefinir-senha` | Fluxos implementados em `/acessar`; rotas dedicadas futuras | Pedido genérico, token inválido/vencido e confirmação | RF-004 |
| UI-04 | `/checkout` | Integração parcial | Cotação, total, parcelas permitidas, consentimentos aplicáveis e envio idempotente | RF-008 |
| UI-05 | `/assinatura` | Planejada | Pedido pendente/pago/recusado, vigência, expiração e instrução de nova contratação | RF-009/010 |
| UI-06 | `/cliente` | Indicadores, próximos passos, atualizações e casos implementados; assinatura pendente | Resumo, últimos casos, pendências e assinatura; sem dados internos | RF-019/038 |
| UI-07 | `/cliente/casos/novo` | Formulário integrado em `/cliente`; anexos pendentes | Rascunho, categoria, relato e documentos; validação antes de submeter | RF-011/016 |
| UI-08 | `/cliente/casos/{id}` | Detalhe, documentos, complemento, conversa e histórico em `/cliente`; demais ações futuras | Status, documentos, procuração, mensagens, pendências, timeline e defesa publicada | RF-015/018/022/023/026/040 |
| UI-09 | `/advogado` | Indicadores, pendências, fila atribuída e filtro implementados; vencimentos pendentes | Fila atribuída, filtros e vencimentos informados | RF-020/038 |
| UI-10 | `/advogado/casos/{id}` | Triagem, documentos, complemento, conversa e notas internas em `/advogado`; demais ações futuras | Triagem, documentos, procuração, notas, minutas, revisão, publicação, protocolo e prazos | RF-012/014/021/027–031/039 |
| UI-11 | `/admin` e subtelas | Convites e atribuição em `/advogado` para ADMIN; demais ações futuras | Usuários, atribuição por metadados, categorias, modelos, financeiro, pedidos de privacidade e auditoria | RF-006/013/032–036 |
| UI-12 | `/perfil` | Planejada | Dados próprios, segurança de sessão, revalidação de e-mail e pedido de privacidade | RF-004/007/036 |
| UI-13 | `/notificacoes` | Central integrada aos painéis, com filtro e leitura persistida; rota dedicada futura | Lista paginada e estado lido/não lido | RF-024 |
| UI-14 | `/termos`, `/privacidade` | Âncoras atuais sem conteúdo correspondente | Texto aprovado, versão, data e canal responsável | RF-037 |

## Estados obrigatórios por tela

**Extensão civil:** UI-07 identifica demanda a iniciar ou processo existente; UI-10 inclui posição do cliente (autor/réu), partes, processo, etapas contratadas, petição inicial/defesa e agenda de audiências. UI-08 mostra etapas e compromissos pertinentes ao cliente; UI-09 agrega audiências e alertas de choque de agenda do advogado. Publicar uma peça não apresenta o processo como encerrado. Requisitos RF-041 a RF-043.

Carregando, vazio, sucesso, erro recuperável, sessão expirada e ação sem permissão. Formulários preservam dados não sensíveis ao falhar e associam erro ao campo. Não preservar cartão ou senha em armazenamento local. Botão desabilitado durante envio ajuda a experiência, mas idempotência deve existir no servidor.

Pagamento pendente apresenta “Aguardando confirmação” e consulta de situação; não mostrar aprovação por simples recebimento de código. Upload mostra progresso, quarentena, liberado ou rejeitado. Erro de scanner explica indisponibilidade sem oferecer bypass. Transição concorrente pede atualização dos dados, evitando sobrescrita silenciosa.

## Navegação e acessibilidade

Menu conforme papel, indicação de página atual e retorno ao caso. Tabelas devem adaptar-se ao celular; documentos e ações principais acessíveis sem rolagem horizontal obrigatória. Foco visível, navegação por teclado, rótulos, contraste e anúncios de status. Status não deve depender apenas de cor. Preservar foco ao abrir/fechar diálogos e exigir motivo em ações administrativas relevantes.

## Conteúdo e privacidade

Separar campo público ao cliente de nota interna com rótulo claro antes do envio. Mostrar somente os dados necessários; mascarar identificadores quando possível. O dashboard ilustrado na landing deve continuar identificado como prévia até existir a funcionalidade validada. Não exibir afirmações de proteção, disponibilidade ou prazo que a operação não consiga comprovar.

Não foram criados mockups novos nesta etapa; os inventários e critérios orientam DEV-024 a DEV-043. Revisão visual e responsiva integra o backlog e o roteiro de homologação.
