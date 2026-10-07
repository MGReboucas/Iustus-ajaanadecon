# Associação Iustus — checkout integrado atualizado em 06/10/2026

Este documento descreve o checkout transparente e substitui o fluxo anterior de redirecionamento ao PagBank. A configuração comercial exige associação paga. Os perfis isolados de testes legados preservam a liberação assistida para regressão.

## Jornada

1. Landing e checkout apresentam **12x de R$ 79,90 sem juros**, total anual de **R$ 958,80**. O preço aparece no HTML inicial mesmo com a API indisponível; a cobrança fica bloqueada enquanto a configuração não estiver pronta.
2. O formulário Next recebe nome, e-mail confirmado, CPF e celular do associado, além do cartão. O SDK oficial PagBank criptografa o cartão no navegador; PAN, validade e CVV não são enviados ao backend Iustus nem persistidos pelo aplicativo. A API aceita apenas o cartão criptografado e envia o pedido para `/orders`, com captura, preço do servidor e exatamente 12 parcelas. O titular do cartão pode ser diferente do associado. Não há redirecionamento externo.
3. Webhook com assinatura ECDSA válida gera um evento durável. O worker consulta o pedido diretamente na API autenticada do PagBank, verifica referência, produto, moeda, valor pago e ausência de estorno. Pedidos integrados também exigem e-mail, CPF e parcelamento correspondentes ao cadastro. A consulta de status do checkout faz a mesma reconciliação autenticada, no máximo a cada 15 segundos por pedido.
4. Apenas pagamento PAID confirmado cria associação e envia acesso. Retorno do navegador, checkout criado, pagamento em análise ou recusado não concedem acesso.
5. Novo associado recebe link de uso único, válido por 24 horas, para informar nome e senha e confirmar a posse do e-mail. Uma conta existente confirmada mantém a senha e recebe instruções para entrar. O reenvio fica em “Já paguei: reenviar acesso”.
6. Associado cadastra título, categoria, descrição, data do ocorrido e documentos. Rascunhos podem ficar incompletos; o envio exige data válida e ao menos um documento próprio liberado pela verificação.
7. O sistema distribui a ocorrência entre advogados ativos e confirmados, priorizando menor quantidade de casos abertos. Com MFA obrigatório, somente advogados habilitados com MFA entram na distribuição. Na ausência de responsável elegível, mantém a fila administrativa e avisa administradores.
8. Advogado inicia análise e aprova, recusa com justificativa ou solicita complemento. O cliente recebe aviso no painel e evento para envio por e-mail.
9. **Após o aceite**, o advogado gera ou anexa a procuração revisada daquele caso e usa “Enviar procuração deste caso para assinatura”. O cliente baixa, assina conforme orientação e devolve nos documentos do mesmo caso. O advogado confere ou pede correção; a preparação só começa depois dessa conferência.
10. Advogado registra preparação, publicação, protocolo externo, compromissos, movimentações e encerramento. O cliente acompanha gráfico, pendências e histórico. Avisos do painel são consultados a cada 30 segundos enquanto a aba está visível.

A assinatura da procuração permanece externa, com devolução do documento assinado. Não foi integrada uma plataforma de assinatura eletrônica nem foram criados poderes jurídicos automaticamente. Modelos são aprovados pelo advogado, e os documentos ficam vinculados ao caso; o backend rejeita documentos de outro caso.

## Vigência e acesso

- A associação vale um ano a partir do pagamento confirmado; nova adesão durante vigência estende o período. Não há renovação/cobrança automática.
- Expiração ou estorno impede novos envios, preservando login e consulta dos casos anteriores.
- Cadastro público livre e liberação administrativa de novos atendimentos ficam desligados no fluxo comercial. Registros históricos de liberação e casos não são apagados.
- O escopo preservado é trânsito e direito civil, exceto família e sucessões.
- Cada caso tem análise individual; associação ativa não significa aceite automático.
- E-mails transacionais de acesso usam a fila de identidade. Avisos de atendimento usam fila própria, respeitam preferências de e-mail e nunca incluem relatos, documentos ou notas internas. Avisos permanecem no painel.

## Aplicação e serviços externos

As alterações estão no código; não significam homologação financeira nem publicação automática. Antes de cobrar:

1. Aplicar `python manage.py migrate --settings=config.settings.production` no ambiente destinado à implantação.
2. Configurar no backend `PAGBANK_ENVIRONMENT=sandbox`, `PAGBANK_API_TOKEN`, `PAGBANK_WEBHOOK_PUBLIC_KEY` e, após preparar os serviços, `BILLING_ENABLED=true`.
3. Criar previamente a chave de cartão com `POST /public-keys`, corpo `{"type":"card"}`, no ambiente correto da conta PagBank; consultar com `GET /public-keys/card`. O endpoint interno `/billing/card-key` expõe somente essa chave pública ao SDK. Consultar a chave pública de webhook da conta pela API oficial, tipo `webhook`, e armazenar o valor Base64/X.509. Atualizar a variável durante rotação. Confirmar com o provedor a disponibilidade do modelo de assinatura e endpoint de chaves para a conta e ambiente produtivo.
4. Manter `IUSTUS_PUBLIC_ORIGIN` HTTPS, `DJANGO_API_ORIGIN` e segredo de proxy coerentes. O webhook público é `/api/v1/billing/webhook`; o proxy preserva os bytes e encaminha somente o header de assinatura apropriado.
5. Configurar SMTP, armazenamento S3 privado e scanner; rodar `python manage.py run_operations`. O worker processa pagamentos, e-mails, lembretes e documentos. O worker garante a reconciliação mesmo após fechar o navegador e é necessário para entregar os e-mails. Não depender somente da consulta de status da página.
6. Homologar pagamento aprovado, pendente, recusado, duplicado, estorno, falha de rede, reenvio de acesso, entrega real de e-mail e upload/download privado.
7. Somente depois da homologação, usar credenciais e chave pública de produção com `PAGBANK_ENVIRONMENT=production`. Nenhuma credencial real foi criada ou alterada nesta implementação.

Quando `BILLING_ENABLED=false`, preço e formulário continuam visíveis, mas o botão de pagamento fica desabilitado. As rotas antigas de pagamento não recebem mais dados de cartão. Dados de sandbox não concedem associação quando o ambiente muda para produção.

## Operação financeira

Para preparar o sandbox sem habilitar cobranças, obtenha o token no [Portal do Desenvolvedor PagBank](https://developer.pagbank.com.br/docs/token-de-autenticacao) e configure `PAGBANK_API_TOKEN` e `PAGBANK_ENVIRONMENT=sandbox` no arquivo privado `backend/.env`. Mantenha `BILLING_ENABLED=false` inicialmente.

```text
backend/.venv/Scripts/python.exe backend/manage.py check_pagbank --settings=config.settings.local
backend/.venv/Scripts/python.exe backend/manage.py check_pagbank --fetch-webhook-key --settings=config.settings.local
backend/.venv/Scripts/python.exe backend/manage.py check_pagbank --fetch-card-key --settings=config.settings.local
```

O segundo comando faz apenas a consulta autenticada da chave pública; não cria checkout nem pagamento. Salva a chave em `.local/pagbank-sandbox-webhook-key.txt`, fora do Git, e mostra somente sua impressão digital. Configure seu conteúdo como `PAGBANK_WEBHOOK_PUBLIC_KEY` na API e no worker. Falha de autenticação, ausência de suporte a esse endpoint ou chave de outro tipo bloqueiam essa preparação e precisam ser resolvidas com a conta/provedor antes de ativar o checkout.

`Order` guarda referência, valor, ambiente, estado, associação com usuário e dados do comprador criptografados. O fingerprint com HMAC fixa os dados da tentativa sem guardar o cartão criptografado; `BillingIdentity` vincula usuário/e-mail a um único CPF por ambiente, com CPF criptografado e índice HMAC. O vínculo só é criado após confirmação do pagamento. CPF válido não equivale a comprovação documental de identidade. Pedidos antigos continuam conciliáveis, sem inventar CPF para registros históricos; `Membership` guarda o período; `PaymentEvent` guarda identificadores, tentativas e processamento, sem armazenar o payload financeiro completo.

Monitorar `PaymentEvent` sem `processed_at`, especialmente `attempts >= 10` ou `last_error` preenchido. A repetição tem espera crescente e não duplica associação/e-mail. O worker reagenda pedidos em análise. Após falha de comunicação, a página permite reenviar somente a mesma tentativa com a mesma referência e dados; não persiste cartão no navegador. Ao recarregar uma tentativa incerta, ou após uma hora sem confirmação, a recuperação exige conferência operacional e reconciliação, nunca um novo débito automático. O uso de e-mail de profissional ou conta desativada exige conferência operacional, sem converter o perfil em cliente.

Se uma notificação não chegar ou esgotar tentativas, use o identificador real do pedido PagBank para consultar novamente:

```text
python manage.py reconcile_payment <uuid-do-pedido-iustus> <ORDE_do_pagbank>
```

O comando verifica o estado diretamente no provedor; não oferece aprovação manual. Identificadores incompatíveis e valores incorretos são rejeitados. Não reaproveitar um pedido estornado para reativação: é necessária nova adesão.

## Validação local

```text
backend/.venv/Scripts/python.exe backend/manage.py test tests --settings=config.settings.test --noinput
npm run build
cd frontend
npx playwright test --config playwright.checkout.config.ts
cd ..
node --test tests/frontend/proxy.test.cjs tests/frontend/documents.test.cjs
```

No Windows, a partir da raiz, `tests/e2e/run-association.ps1` prepara o SQLite E2E isolado e executa Chrome nas portas 3011/8011. O pagamento e o scanner são simulados somente nas fixtures; os endpoints de aplicação permanecem reais. Os testes cobrem ativação, data/anexos, distribuição, aprovação, procuração específica, devolução e conferência, além de layout móvel. A suíte de concorrência exige PostgreSQL e usa `config.settings.test_postgres` com `TEST_DATABASE_URL` apontando para um banco exclusivo de testes.

## Referências do provedor consultadas

- [Criar e pagar pedido com cartão / SDK](https://developer.pagbank.com.br/reference/criar-pagar-pedido-com-cartao)
- [Criar chave pública](https://developer.pagbank.com.br/reference/criar-chave-publica)
- [Consultar chave pública](https://developer.pagbank.com.br/reference/consultar-chave-publica)
- [Validação da assinatura da notificação](https://developer.pagbank.com.br/reference/validacao-de-autenticidade)
