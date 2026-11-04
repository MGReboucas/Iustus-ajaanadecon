# Mercado Pago — compra anual sem renovação automática

Decisão atual: R$ 699,90 em 10 parcelas de R$ 69,99, com vigência de um ano. Renovação somente por uma nova compra autorizada pelo associado. Não há cobrança automática no aniversário da adesão.

## Fluxo

- Next usa Card Payment Brick; o app React Native abre o checkout no navegador externo.
- O backend envia uma compra comum a `POST /v1/orders`, com e-mail do pagador, token temporário e dez parcelas. Não cria clientes/perfis, não solicita armazenamento de cartão nem envia `stored_credential` ou `automatic_payments`.
- Não há dependência da habilitação comercial de Pagamentos Automáticos. `MERCADOPAGO_AUTOMATIC_PAYMENTS_ENABLED` foi removida e pode ser apagada da Render e do `.env`.
- O scheduler não agenda renovações. Eventos antigos de renovação ainda não enviados são cancelados sem chamada de cobrança. Pagamentos já enviados continuam sendo conciliados para não perder confirmações e estornos.
- Payloads pendentes da implementação recorrente não são enviados. O novo plano versionado exige atualizar o checkout antes de pagar.
- Somente confirmação autenticada de order/transação processada e creditada libera acesso. Validações de valor, dez parcelas, conta, ambiente e total sem juros continuam ativas.
- Duplicatas e timeouts preservam a mesma referência e chave de idempotência. Estornos e contestações revogam o acesso correspondente. O período pago e casos existentes não são cancelados pela remoção da recorrência.
- O modelo interno Subscription permanece por compatibilidade de banco e histórico. Compras confirmadas ficam COMPLETED, sem próxima cobrança; isso não representa uma assinatura automática no Mercado Pago.
- Pedidos numéricos antigos Payments e histórico PagBank mantêm conciliação compatível. Não se convertem em novas cobranças.

## Configurar backend e worker na Render

Use o [modelo de variáveis](../infra/deploy/mercadopago.env.example). O Access Token e o segredo de webhook nunca vão para variáveis públicas do frontend.

1. Publicar o código atualizado e aplicar migrações anteriores pendentes com `python manage.py migrate`. Esta alteração não exige novo esquema.
2. Configurar `BILLING_PROVIDER=mercadopago`, `MERCADOPAGO_ENVIRONMENT=sandbox`, `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_PUBLIC_KEY` e `MERCADOPAGO_COLLECTOR_ID` da conta recebedora de teste, não o ID da aplicação. Manter `BILLING_ENABLED=false` enquanto prepara.
3. Executar `python manage.py check_mercadopago --remote`. Consulta somente `/users/me`; não cobra e não imprime segredos.
4. Configurar evento **order** para `https://SEU-DOMINIO-DO-PORTAL/api/v1/billing/mercadopago/webhook` e guardar a assinatura em `MERCADOPAGO_WEBHOOK_SECRET`. O Next encaminha ao Django preservando os campos de assinatura.
5. Confirmar dez parcelas sem juros e configurar `MERCADOPAGO_INTEREST_FREE_CONFIRMED=true`. Depois, habilitar somente o ambiente de teste com `BILLING_ENABLED=true`. Não trocar para produção para tentar contornar recusas de autenticação.
6. Manter `python manage.py run_operations` no worker para conciliação e e-mails, sem renovação automática. Para o app, configurar `MOBILE_EXTERNAL_CHECKOUT_ENABLED` conforme o canal de distribuição.
7. Homologar com cartão fictício oficial: aprovação, recusa, webhook real, retorno ao app, dez parcelas, timeout, estorno e nova compra manual. Só depois configurar ambiente e credenciais produtivas.

Conciliação autenticada: `python manage.py reconcile_payment UUID_LOCAL ORD...`.

## Limitação atual

Após a revisão da credencial pelo titular, as consultas `/users/me` e `/v1/payment_methods` retornaram HTTP 200. A consulta a Orders com ID fictício retornou HTTP 404, como esperado. O collector ID da conta de teste foi preenchido no `.env` local. O erro anterior de autenticação não se repetiu. Ainda faltam configurar a assinatura do webhook, confirmar o parcelamento sem juros e homologar a compra completa. Nenhuma cobrança foi criada. As credenciais não foram expostas nem versionadas; a configuração local não é transferida automaticamente para a Render.

Testes locais cobrem a ausência de criação de perfis, bloqueio de renovações antigas, compra manual subsequente, confirmação, estorno, duplicidade, proxy e interfaces Next/Expo. Esses testes não substituem a homologação na conta Mercado Pago.

[Integração oficial de cartões via Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-integration/websites/cards).
