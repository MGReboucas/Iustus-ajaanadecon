from copy import deepcopy
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.identity.security import IdentityError
from integrations.mercadopago import orders
from .test_mercadopago import CONFIG


def snapshot():
    return {"id": "ORD01JS2V6CM8KJ0EC4H502TGK1WP", "type": "online", "user_id": "123", "country_code": "BRA",
            "external_reference": "reference", "status": "processed", "status_detail": "accredited",
            "total_amount": "699.90", "total_paid_amount": "699.90", "last_updated_date": "2026-11-04T15:00:00Z",
            "transactions": {"payments": [{"id": "PAY01JS2V6CM8KJ0EC4H504R7YE34", "amount": "699.90", "paid_amount": "699.90",
                "status": "processed", "status_detail": "accredited", "reference_id": "ref123",
                "payment_method": {"id": "visa", "type": "credit_card", "installments": 10, "installment_amount": "69.99"},
                "automatic_payments": {"payment_profile_id": "profile123"}}]}}


@override_settings(**CONFIG)
class OrdersContractTests(SimpleTestCase):
    def test_authenticated_lookup_uses_orders_endpoint_and_checks_account(self):
        with patch.object(orders, "request_api", side_effect=[{"id": 123, "tags": ["test_user"]}, snapshot()]) as api:
            result = orders.payment(snapshot()["id"])
        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["installments"], 10)
        self.assertEqual(result["paymentProfileId"], "profile123")
        self.assertEqual(api.call_args_list[1].args[0], "/v1/orders/" + snapshot()["id"])

    def test_production_credential_cannot_be_used_in_sandbox(self):
        with patch.object(orders, "request_api", return_value={"id": 123, "tags": []}) as api:
            with self.assertRaises(IdentityError):
                orders.payment(snapshot()["id"])
        self.assertEqual(api.call_count, 1)

    def test_pending_authorization_and_mixed_statuses_never_approve(self):
        for state, detail in [("processing", "in_process"), ("action_required", "waiting_capture"), ("action_required", "pending_challenge"), ("in_review", "in_review")]:
            data = snapshot(); data.update(status=state, status_detail=detail)
            self.assertEqual(orders.normalize(data)["status"], "pending")
        data = snapshot(); data["transactions"]["payments"][0]["status"] = "processing"
        self.assertEqual(orders.normalize(data)["status"], "pending")

    def test_full_and_partial_refunds_and_chargebacks_override_approval(self):
        for state, detail, expected in [("refunded", "refunded", "refunded"), ("processed", "partially_refunded", "refunded"), ("charged_back", "in_process", "charged_back")]:
            data = snapshot(); tx = data["transactions"]["payments"][0]; tx.update(status=state, status_detail=detail)
            self.assertEqual(orders.normalize(data)["status"], expected)
        data = snapshot(); data["transactions"]["chargebacks"] = [{"id": "dispute"}]
        self.assertEqual(orders.normalize(data)["status"], "charged_back")

    def test_ambiguous_transactions_and_interest_are_rejected(self):
        data = snapshot(); data["transactions"]["payments"] *= 2
        with self.assertRaises(IdentityError): orders.normalize(data)
        for field, value in [("amount", "1.00"), ("paid_amount", "800.00")]:
            data = snapshot(); data["transactions"]["payments"][0][field] = value
            with self.assertRaises(IdentityError): orders.normalize(data)
        data = snapshot(); data["transactions"]["payments"][0]["payment_method"]["installment_amount"] = "80.00"
        with self.assertRaises(IdentityError): orders.normalize(data)

    def test_untrusted_identifier_never_reaches_transport(self):
        with patch.object(orders, "request_api") as api:
            for value in ["../users/me", "ORD?token=x", "https://example.com", "ORDabc"]:
                with self.assertRaises(IdentityError): orders.payment(value)
        api.assert_not_called()

    def test_http_402_keeps_created_order_for_authenticated_reconciliation(self):
        import io, json
        from urllib.error import HTTPError
        from integrations.mercadopago.client import request_api
        data = snapshot(); data["status"] = "failed"
        error = HTTPError("https://api.mercadopago.com/v1/orders", 402, "failed", {}, io.BytesIO(json.dumps(data).encode()))
        with patch("integrations.mercadopago.client.build_opener") as opener:
            opener.return_value.open.side_effect = error
            result = request_api("/v1/orders", {"external_reference": "reference"}, "key")
        self.assertEqual(result["id"], data["id"])
        self.assertEqual(result["status"], "failed")

    def test_http_402_without_matching_order_remains_uncertain(self):
        import io, json
        from urllib.error import HTTPError
        from integrations.mercadopago.client import request_api
        error = HTTPError("https://api.mercadopago.com/v1/orders", 402, "failed", {}, io.BytesIO(json.dumps(snapshot()).encode()))
        with patch("integrations.mercadopago.client.build_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(IdentityError): request_api("/v1/orders", {"external_reference": "different"}, "key")

    def test_single_payment_response_needs_no_profile(self):
        data = snapshot()
        del data["transactions"]["payments"][0]["automatic_payments"]
        self.assertEqual(orders.normalize(data)["status"], "approved")
