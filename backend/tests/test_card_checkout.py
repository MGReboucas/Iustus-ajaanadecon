import copy
import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.billing.checkout import fingerprint
from apps.billing.models import BillingIdentity, Membership, Order, PaymentEvent
from apps.billing.services import reconcile
from apps.identity.models import User
from apps.identity.security import IdentityError, decrypt, encrypt
from integrations.pagbank.client import create_card_order, card_public_key
from jobs.billing import process_payment
from .test_identity import IdentityTests


def payment_body():
    return {"accepted": True, "customer": {"name": "Associado Teste", "email": "buyer@example.test",
        "cpf": "12345678909", "phone": "11999999999"},
        "card": {"encrypted": "A" * 344, "holderName": "Titular Teste", "holderCpf": "52998224725"}}


@override_settings(BILLING_ENABLED=True, PAGBANK_ENVIRONMENT="sandbox", IDENTITY_SHARED_PORTAL=True)
class CardCheckoutTests(TestCase):
    browser = IdentityTests.browser

    def submit(self, browser, body=None, key="synthetic-card-checkout-001"):
        csrf = browser.get("/api/v1/auth/csrf").json()["csrfToken"]
        return browser.post("/api/v1/billing/checkout", body or payment_body(), content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf, HTTP_IDEMPOTENCY_KEY=key)

    def snapshot(self, order, status="PAID"):
        return {"id": "ORDE_synthetic", "reference_id": str(order.pk),
            "customer": {"name": "Associado Teste", "email": "buyer@example.test", "tax_id": "12345678909"},
            "items": [{"reference_id": "iustus-associacao-anual", "quantity": 1, "unit_amount": order.amount}],
            "charges": [{"status": status, "paid_at": timezone.now().isoformat(),
                "amount": {"value": order.amount, "currency": "BRL", "summary": {"paid": order.amount if status == "PAID" else 0, "refunded": 0}},
                "payment_method": {"type": "CREDIT_CARD", "installments": 12}}]}

    def create(self):
        browser = self.browser()
        with patch("apps.billing.views.create_card_order", return_value="ORDE_synthetic"):
            self.assertEqual(self.submit(browser).status_code, 201)
        return browser, Order.objects.get()

    def test_retries_keep_reference_and_session_even_after_timeout(self):
        browser = self.browser()
        with patch("apps.billing.views.create_card_order", side_effect=IdentityError("PROVIDER", "Timeout", 503)):
            self.assertEqual(self.submit(browser).status_code, 503)
        original = Order.objects.get()
        self.assertEqual(browser.get("/api/v1/billing/checkout").json()["status"], "CREATING")
        with patch("apps.billing.views.create_card_order", return_value="ORDE_synthetic") as provider:
            self.assertEqual(self.submit(browser).status_code, 201)
            self.assertEqual(self.submit(browser).status_code, 201)
            self.assertEqual(provider.call_count, 1)
        self.assertEqual(Order.objects.get().pk, original.pk)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(self.browser().get("/api/v1/billing/checkout").status_code, 404)
        self.assertFalse(Membership.objects.exists())
        self.assertNotIn("buyer@example.test", original.encrypted_customer)
        self.assertEqual(json.loads(decrypt(original.encrypted_customer))["cpf"], "12345678909")
        self.assertNotIn("A" * 344, str(vars(original)))

    def test_invalid_cpf_card_plaintext_or_client_price_never_reach_provider(self):
        bodies = []
        for field, value in [("cpf", "11111111111"), ("cpf", "12345678901"), ("email", "invalid"), ("phone", "123")]:
            body = payment_body(); body["customer"][field] = value; bodies.append(body)
        for field, value in [("cvv", "123"), ("number", "4111111111111111")]:
            body = payment_body(); body["card"][field] = value; bodies.append(body)
        body = payment_body(); body["amount"] = 1; bodies.append(body)
        body = payment_body(); body["installments"] = 1; bodies.append(body)
        body = payment_body(); body["accepted"] = False; bodies.append(body)
        with patch("apps.billing.views.create_card_order") as provider:
            for body in bodies:
                self.assertIn(self.submit(self.browser(), body).status_code, (400, 422))
            provider.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_payload_is_fixed_price_and_cardholder_is_separate_from_associate(self):
        order = Order.objects.create(request_key=uuid4().hex, session_digest=uuid4().hex, amount=95880, environment="sandbox", policy_version="test")
        body = payment_body()
        with patch("integrations.pagbank.client.request_api", return_value={"id": "ORDE_test", "reference_id": str(order.pk)}) as provider:
            create_card_order(order, body["customer"], body["card"])
        path, data, key = provider.call_args.args
        self.assertEqual(path, "/orders")
        self.assertEqual(key, order.pk)
        self.assertEqual(data["customer"]["tax_id"], "12345678909")
        self.assertEqual(data["charges"][0]["amount"], {"value": 95880, "currency": "BRL"})
        method = data["charges"][0]["payment_method"]
        self.assertEqual(method["installments"], 12)
        self.assertTrue(method["capture"])
        self.assertEqual(method["holder"]["tax_id"], "52998224725")
        self.assertFalse(method["card"]["store"])
        self.assertNotIn("fees", method)

    def test_verified_payment_binds_buyer_cpf_and_is_idempotent(self):
        browser, order = self.create()
        with patch("apps.billing.services.request_api", return_value=self.snapshot(order)):
            self.assertEqual(browser.get("/api/v1/billing/checkout").json()["status"], "PAID")
            reconcile(order.pk, "ORDE_synthetic")
        identity = BillingIdentity.objects.get()
        self.assertEqual(identity.user.email, "buyer@example.test")
        self.assertEqual(decrypt(identity.encrypted_cpf), "12345678909")
        self.assertNotEqual(identity.cpf_digest, "12345678909")
        self.assertEqual(Membership.objects.count(), 1)
        self.assertFalse(identity.user.has_usable_password())

    def test_paid_snapshot_must_match_email_cpf_price_and_installments(self):
        _, order = self.create()
        original = self.snapshot(order)
        for field in ("email", "cpf", "amount", "installments"):
            data = copy.deepcopy(original)
            if field == "email": data["customer"]["email"] = "other@example.test"
            if field == "cpf": data["customer"]["tax_id"] = "52998224725"
            if field == "amount": data["charges"][0]["amount"]["value"] += 100
            if field == "installments": data["charges"][0]["payment_method"]["installments"] = 1
            with patch("apps.billing.services.request_api", return_value=data), self.assertRaises(IdentityError):
                reconcile(order.pk, "ORDE_synthetic")
        self.assertFalse(User.objects.exists())
        self.assertFalse(BillingIdentity.objects.exists())
        self.assertFalse(Membership.objects.exists())

    def test_bound_identity_cannot_switch_email_or_cpf_before_charge(self):
        user = User.objects.create_user("buyer@example.test", None)
        BillingIdentity.objects.create(user=user, environment="sandbox", cpf_digest=fingerprint("cpf:12345678909"), encrypted_cpf=encrypt("12345678909"))
        with patch("apps.billing.views.create_card_order") as provider:
            for field, value in [("email", "other@example.test"), ("cpf", "52998224725")]:
                body = payment_body(); body["customer"][field] = value
                self.assertEqual(self.submit(self.browser(), body).status_code, 422)
            provider.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_changed_payload_new_key_and_stale_uncertain_order_do_not_charge_again(self):
        browser = self.browser()
        with patch("apps.billing.views.create_card_order", side_effect=IdentityError("PROVIDER", "Timeout", 503)):
            self.submit(browser)
        body = payment_body(); body["customer"]["name"] = "Outro Nome"
        with patch("apps.billing.views.create_card_order") as provider:
            self.assertEqual(self.submit(browser, body).status_code, 409)
            self.assertEqual(self.submit(browser, key="another-synthetic-key").status_code, 409)
            Order.objects.update(created_at=timezone.now() - timedelta(hours=2))
            self.assertEqual(self.submit(browser).status_code, 409)
            provider.assert_not_called()

    def test_pending_worker_retries_and_decline_does_not_activate(self):
        _, order = self.create()
        with patch("apps.billing.services.request_api", return_value=self.snapshot(order, "IN_ANALYSIS")):
            self.assertTrue(process_payment())
        event = PaymentEvent.objects.get()
        self.assertIsNone(event.processed_at)
        self.assertGreater(event.available_at, timezone.now())
        with patch("apps.billing.services.request_api", return_value=self.snapshot(order, "DECLINED")):
            reconcile(order.pk, "ORDE_synthetic")
        self.assertFalse(Membership.objects.exists())
        self.assertEqual(Order.objects.get().status, "DECLINED")

    def test_card_key_exposes_only_public_key_and_disabled_billing_blocks_charge(self):
        with patch("integrations.pagbank.client.request_api", return_value={"public_key": "A" * 344}) as provider:
            result = self.browser().get("/api/v1/billing/card-key")
            self.assertEqual(result.json(), {"publicKey": "A" * 344})
            provider.assert_called_once_with("/public-keys/card")
        with patch("integrations.pagbank.client.request_api", return_value={}):
            with self.assertRaises(IdentityError): card_public_key()
        with override_settings(BILLING_ENABLED=False), patch("apps.billing.views.create_card_order") as provider:
            self.assertEqual(self.submit(self.browser()).status_code, 503)
            provider.assert_not_called()

    def test_missing_csrf_does_not_start_payment(self):
        with patch("apps.billing.views.create_card_order") as provider:
            result = self.browser().post("/api/v1/billing/checkout", payment_body(), content_type="application/json", HTTP_IDEMPOTENCY_KEY="synthetic-card-checkout-001")
            self.assertEqual(result.status_code, 403)
            provider.assert_not_called()
