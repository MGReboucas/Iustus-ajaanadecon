# Mercado Pago — checkout e renovação anual

> Estado atual: o código ainda usa Payments API. A aplicação do painel foi criada como Orders; a migração e os testes de Orders estão pendentes. Não habilitar cobranças com base apenas nos testes descritos abaixo. Para Mercado Pago, as variáveis `PAGBANK_*` são dispensáveis; referências de backend/testes/migrações legadas permanecem no repositório.

Atualização: 04/11/2026. Condição confirmada: R$ 699,90 por ano, em 10 parcelas de R$ 69,99, com renovação automática anual nas mesmas condições. Cada ciclo é uma compra anual parcelada; não são dez mensalidades independentes.

## Dependência externa obrigatória

O titular confirmou possuir apenas a conta aprovada. O produto [Pagamentos Automáticos exige habilitação comercial da aplicação para pagamentos sem CVV](https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/prerequisites). A aprovação da conta não comprova essa habilitação, nem o suporte comercial ?s dez parcelas sem juros em cada cobrança anual iniciada pelo estabelecimento (MIT). Confirmar ambos com o Mercado Pago antes de habilitar produção.

A implementação usa [Payments API e cartão salvo](https://www.mercadopago.com.br/developers/pt/docs/automatic-payments/recurring-charges), com Card Payment Brick no navegador, e não o Checkout Pro ou uma assinatura mensal. Não há homologação real sem credenciais e liberação. Não mudar silenciosamente a oferta para cobrança anual à vista ou assinatura mensal.

## Fluxo implementado

- Next: cadastro, validação de CPF/e-mail, aceite versionado da oferta e renovação, cartão em campos do SDK oficial e confirmação consultada no servidor.
- React Native/Expo: checkout abre no navegador externo no portal; não coleta cartão em WebView. Consulta e cancelamento da renovação são nativos, autenticados por bearer. Ao voltar à tela/app, as consultas são atualizadas. Primeiro acesso é ativado pelo link de e-mail.
- Django registra a identidade cifrada, consentimento e condições imutáveis por pedido/assinatura. Guarda referências cifradas ao cofre MP, nunca PAN/CVV.
- Reenvio após timeout usa o mesmo pedido, chave de idempotência e payload cifrado. O token de pagamento temporário é apagado após obter o ID ou conciliar. Tentativas incertas antigas exigem conferência; não iniciar novo débito automaticamente.
- Confirmação valida ID, referência, conta recebedora, ambiente, pagador do cofre, moeda, valor integral, total sem juros e dez parcelas. Redirect/query do navegador nunca ativa acesso.
- Webhook HMAC é validado com `data.id`, `x-request-id` e `x-signature`; consulta autenticada precede a fila durável. Duplicatas não duplicam vigência nem e-mail. Estorno parcial/total e chargeback revogam acesso daquele pagamento e interrompem a renovação, preservando casos.
- Worker agenda o próximo ciclo no vencimento da vigência confirmada. Bloqueia assinatura durante decisão de cancelamento/cobrança. Recusa definitiva não dispara novas tentativas de cobrança automática; fica em conferência para atendimento.
- Cancelar a próxima renovação preserva a vigência paga. Uma operação já enviada ao provedor deve ser conciliada; cancelamento não representa estorno de cobrança já iniciada.
- Pedidos históricos PagBank continuam com seu provedor e condições originais. Não são convertidos em autorizações recorrentes.

## Configuração e publicação

Use [modelo de variáveis](../infra/deploy/mercadopago.env.example) no backend. Nenhum Access Token ou segredo de webhook pertence a `NEXT_PUBLIC_*` ou `EXPO_PUBLIC_*`. A public key é entregue pela API somente quando a configuração permite checkout.

1. Criar aplicação Mercado Pago e solicitar a habilitação de Pagamentos Automáticos, confirmando 10x sem juros em CIT e MIT anuais.
2. Configurar credenciais do mesmo ambiente e `MERCADOPAGO_COLLECTOR_ID` da conta recebedora. `sandbox` usa conta/cartão de teste e exige pagamentos com `live_mode=false`.
3. Configurar URL HTTPS pública em `IUSTUS_PUBLIC_ORIGIN`, proxy Next → Django, banco e chave de cifra persistente.
4. Cadastrar webhook de pagamentos em `https://SEU-DOMINIO/api/v1/billing/mercadopago/webhook`; guardar sua assinatura secreta no backend. Usar notificações do tipo `payment`.
5. Aplicar migrações: `python manage.py migrate`. Executar `python manage.py check_mercadopago --remote`. Essa checagem só consulta a conta; não certifica recorrência.
6. Com liberação e condições confirmadas, habilitar os dois flags Mercado Pago e `BILLING_ENABLED=true` no ambiente de teste. Liberar `MOBILE_EXTERNAL_CHECKOUT_ENABLED` por canal de distribuição aplicável.
7. Manter `python manage.py run_operations` ativo para conciliação, renovação e e-mails. Monitorar `PaymentEvent` não processados com dez tentativas e assinaturas `PAST_DUE`/`REVIEW`. O worker não deve ficar parado entre os aniversários.
8. Homologar cartão aprovado/recusado, timeout, notificação repetida, parcelamento sem juros, renovação CIT→MIT, cancelamento, estorno, e-mail e retorno ao app em Android/iOS reais. Não usar dinheiro/cartões reais em testes automatizados.
9. Somente após homologação, configurar credenciais produtivas e `MERCADOPAGO_ENVIRONMENT=production`, conferir domínio/worker e testar a operação autorizada.

Conferência manual segura: `python manage.py reconcile_payment UUID_DO_PEDIDO ID_NUMERICO_DO_PAGAMENTO`. Consulta o provedor; não permite aprovação manual.

## Verificações locais

Testes de contrato/backend usam snapshots sintéticos do provedor. Testes Playwright usam SDK/API simulados para verificar interface e payloads; não constituem certificação do SDK ou conta Mercado Pago. Validações executadas: suíte completa de 207 testes no backend (seis dependentes de PostgreSQL ignorados nessa execução); suíte financeira final de 64 testes aprovada; 39 testes aprovados em PostgreSQL isolado, incluindo concorrência real de envio/confirmação; 12 testes de checkout/painel Next e 2 de associação React Native no Edge; 9 testes do proxy e 5 do transporte nativo; tipos e lint do app, build Next e exportação Expo para Android/iOS/web aprovados. Não houve deploy, migração do banco operacional ou cobrança real.

Limitações de homologação: sem credenciais Mercado Pago no ambiente, sem autorização comercial do produto, sem pagamento real e sem teste em aparelhos físicos. A experiência nativa de compra usa o portal externo; os testes Expo web não substituem builds instalados.
