# billing

Adesão anual, pedidos, confirmação financeira, eventos duráveis e associação com vigência. Checkout hospedado PagBank; o adaptador transparente foi desativado.

Endpoints: `billing/plan`, `billing/checkout`, `billing/webhook`, `billing/activate` e `billing/resend`. O worker consulta o pagamento no provedor antes de ativar a associação. Detalhes, configuração e limitações em [ASSOCIACAO.md](../../../docs/ASSOCIACAO.md). Migrações pertencem ao Django; não criar tabelas pelo frontend.
