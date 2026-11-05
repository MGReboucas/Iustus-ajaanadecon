import hashlib
import hmac
import json
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.billing.models import Order, Membership, Subscription, PaymentEvent
from apps.billing.mercadopago import start_order, send_order, reconcile_payment, renew_due, cancel_renewal, decode
from apps.billing.services import active_memberships
from apps.identity.models import IdentityEmail
from apps.identity.security import IdentityError
from integrations.mercadopago.orders import verify_signature, payment_payload, validate_payment, request_api
from jobs.billing import process_payment
from .test_identity import IdentityTests


def body():
    return {"accepted": True, "automaticRenewal": False, "planVersion": settings.MEMBERSHIP_PLAN_VERSION,
        "policyVersion": settings.REGISTRATION_POLICY_VERSION,
        "customer": {"name": "Associado Teste", "email": "buyer@example.test", "cpf": "12345678909", "phone": "11999999999"},
        "card": {"token": "synthetic_token_123456", "paymentMethodId": "visa", "issuerId": "25", "installments": 10}}


CONFIG = dict(BILLING_ENABLED=True, BILLING_PROVIDER="mercadopago", MERCADOPAGO_ENVIRONMENT="sandbox",
    MERCADOPAGO_ACCESS_TOKEN="synthetic-access", MERCADOPAGO_PUBLIC_KEY="synthetic-public",
    MERCADOPAGO_WEBHOOK_SECRET="synthetic-webhook", MERCADOPAGO_COLLECTOR_ID="123",
    MERCADOPAGO_AUTOMATIC_PAYMENTS_ENABLED=True, MERCADOPAGO_INTEREST_FREE_CONFIRMED=True,
    IDENTITY_SHARED_PORTAL=True)


@override_settings(**CONFIG)
class MercadoPagoTests(TestCase):
    browser = IdentityTests.browser
    post = IdentityTests.post
    user = IdentityTests.user
    login = IdentityTests.login

    def submit(self, browser, data=None, key="synthetic-payment-key-001"):
        csrf = browser.get("/api/v1/auth/csrf").json()["csrfToken"]
        return browser.post("/api/v1/billing/checkout", data or body(), content_type="application/json",
                            HTTP_X_CSRFTOKEN=csrf, HTTP_IDEMPOTENCY_KEY=key)

    def provider(self, path, payload=None, key=None, **kwargs):
        if path == "/users/me":
            return {"id": 123, "tags": ["test_user"]}
        if path.startswith("/v1/customers/search"):
            return {"results": [{"id": "customer_123", "email": "buyer@example.test"}]}
        if "/payment-profiles/" in path:
            return {"id": "profile_123", "status": "READY", "sequence_control": "MANUAL",
                    "payment_methods": [{"status": "READY", "id": "visa", "type": "credit_card"}]}
        if path == "/v1/orders":
            return {"id": "ORD01JS2V6CM8KJ0EC4H502TGK1WP", "external_reference": payload["external_reference"]}
        raise AssertionError(path)

    def create(self):
        browser = self.browser()
        with patch("integrations.mercadopago.orders.request_api", side_effect=self.provider):
            result = self.submit(browser)
        self.assertEqual(result.status_code, 201, result.content)
        return browser, Order.objects.get()

    def test_sandbox_creation_retains_id_and_retries_do_not_charge_again(self):
        browser = self.browser()
        sandbox_id = "ORDTST01M6M5MYRCKEXHNCSTPF06A5T7"
        def provider(path, payload=None, key=None, **kwargs):
            if path == "/v1/orders":
                return {"id": sandbox_id, "external_reference": payload["external_reference"]}
            return self.provider(path, payload, key, **kwargs)
        with patch("integrations.mercadopago.orders.request_api", side_effect=provider):
            result = self.submit(browser)
        self.assertEqual(result.status_code, 201, result.content)
        order = Order.objects.get()
        self.assertEqual(order.provider_order_id, sandbox_id)
        self.assertEqual(order.status, "WAITING")
        with patch("integrations.mercadopago.orders.request_api") as api:
            send_order(order.pk)
        api.assert_not_called()
        self.assertFalse(Membership.objects.exists())

    def snapshot(self, order, status="approved"):
        return {"id": order.provider_order_id or "ORD01JS2V6CM8KJ0EC4H502TGK1WP", "external_reference": str(order.pk), "collector_id": 123,
            "live_mode": False, "payer": {"email": "buyer@example.test"}, "currency_id": "BRL",
            "transaction_amount": order.amount / 100, "installments": order.installments, "payment_type_id": "credit_card",
            "transaction_details": {"total_paid_amount": order.amount / 100}, "transaction_amount_refunded": 0,
            "status": status, "date_approved": timezone.now().isoformat(), "orders_api": True,
            "paymentProfileId": "profile_123", "transactionReference": "reference_123"}

    def confirm(self, order, snapshot=None):
        with patch("integrations.mercadopago.orders.payment", return_value=snapshot or self.snapshot(order)):
            return reconcile_payment(order.pk, order.provider_order_id or "ORD01JS2V6CM8KJ0EC4H502TGK1WP")

    def test_configuration_no_longer_requires_automatic_payments(self):
        with override_settings(MERCADOPAGO_AUTOMATIC_PAYMENTS_ENABLED=False):
            plan = self.browser().get("/api/v1/billing/plan").json()
            self.assertTrue(plan["available"])
            self.assertFalse(plan["automaticRenewal"])

    def test_checkout_is_idempotent_and_does_not_store_raw_card_data(self):
        browser, order = self.create()
        with patch("integrations.mercadopago.orders.request_api") as provider:
            self.assertEqual(self.submit(browser).status_code, 201)
            provider.assert_not_called()
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertFalse(Membership.objects.exists())
        self.assertEqual(order.encrypted_payment_payload, "")
        self.assertNotIn("buyer@example.test", order.encrypted_customer)
        self.assertNotIn("synthetic_token", str(vars(order)))
        self.assertEqual(self.browser().get("/api/v1/billing/checkout").status_code, 404)

    def test_acceptance_plan_installments_and_unknown_card_fields_are_rejected(self):
        for change in ({"automaticRenewal": True}, {"accepted": False}, {"planVersion": "old"}, {"amount": 1}):
            data = body(); data.update(change)
            with self.subTest(change=change), patch("integrations.mercadopago.orders.request_api") as provider:
                self.assertIn(self.submit(self.browser(), data).status_code, (400, 409, 422))
                provider.assert_not_called()
        for change in ({"cvv": "123"}, {"number": "4111111111111111"}, {"installments": 11}):
            data = body(); data["card"].update(change)
            self.assertIn(self.submit(self.browser(), data).status_code, (400, 409, 422))
        self.assertFalse(Order.objects.exists())

    def test_selected_installments_are_persisted_and_sent_to_provider(self):
        data = body(); data["card"]["installments"] = 3
        with patch("integrations.mercadopago.orders.request_api", side_effect=self.provider) as provider:
            response = self.submit(self.browser(), data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.get().installments, 3)
        payload = [call.args[1] for call in provider.call_args_list if call.args[0] == "/v1/orders"][0]
        self.assertEqual(payload["transactions"]["payments"][0]["payment_method"]["installments"], 3)

    def test_lost_response_reuses_exact_persisted_payload_and_key(self):
        browser = self.browser(); calls = []
        def fail(path, payload=None, key=None, **kwargs):
            if path == "/v1/orders":
                calls.append((deepcopy(payload), key))
                raise IdentityError("TIMEOUT", "Timeout", 503)
            return self.provider(path, payload, key)
        with patch("integrations.mercadopago.orders.request_api", side_effect=fail):
            self.assertEqual(self.submit(browser).status_code, 503)
        order = Order.objects.get()
        self.assertTrue(order.encrypted_payment_payload)
        self.assertTrue(PaymentEvent.objects.filter(order=order).exists())
        def succeed(path, payload=None, key=None, **kwargs):
            if path == "/users/me":
                return self.provider(path, payload, key, **kwargs)
            self.assertEqual(path, "/v1/orders")
            calls.append((deepcopy(payload), key))
            return self.provider(path, payload, key)
        with patch("integrations.mercadopago.orders.request_api", side_effect=succeed):
            self.assertEqual(self.submit(browser).status_code, 201)
        self.assertEqual(calls[0], calls[1])

    def test_changed_retry_and_second_session_cannot_duplicate_subscription(self):
        browser, order = self.create()
        changed = body(); changed["customer"]["name"] = "Outro Nome"
        self.assertEqual(self.submit(browser, changed).status_code, 409)
        self.assertEqual(self.submit(self.browser(), key="different-request-key-002").status_code, 409)
        self.assertEqual(Order.objects.count(), 1)

    def test_confirmation_activates_once_and_preserves_annual_terms(self):
        _, order = self.create()
        confirmed = self.confirm(order)
        self.confirm(confirmed)
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(IdentityEmail.objects.count(), 1)
        self.assertTrue(active_memberships(confirmed.user).exists())
        sub = Subscription.objects.get()
        self.assertEqual(sub.status, "COMPLETED")
        self.assertIsNone(sub.next_charge_at)

    def test_mismatched_amount_currency_collector_environment_and_payer_never_activate(self):
        _, order = self.create()
        for change in ({"transaction_amount": 1}, {"currency_id": "USD"}, {"collector_id": 999},
                       {"live_mode": True}, {"payer": {"email": "other"}}, {"external_reference": "other"},
                       {"installments": 1}, {"payment_type_id": "pix"},
                       {"transaction_details": {"total_paid_amount": 800}}, {"date_approved": "invalid"}):
            snapshot = self.snapshot(order); snapshot.update(change)
            with self.subTest(change=change), self.assertRaises(IdentityError):
                self.confirm(order, snapshot)
        self.assertFalse(Membership.objects.exists())

    def test_rejected_payment_never_activates_and_allows_new_subscription(self):
        _, order = self.create()
        self.confirm(order, self.snapshot(order, "rejected"))
        self.assertEqual(Subscription.objects.get().status, "CANCELED")
        self.assertFalse(Membership.objects.exists())
        new = start_order(body(), "new-session", "new-request-key-001")
        self.assertNotEqual(new.pk, order.pk)

    def test_amount_mismatch_becomes_visible_review_and_can_archive_test(self):
        browser, order = self.create()
        with patch("integrations.mercadopago.orders.payment", side_effect=IdentityError("PAYMENT_AMOUNT_MISMATCH", "Mismatch", 422)):
            response = browser.get("/api/v1/billing/checkout")
        self.assertEqual(response.json()["status"], "REVIEW_AMOUNT")
        self.assertFalse(Membership.objects.exists())
        self.assertEqual(self.post(browser, "billing/checkout/reset-test", {"confirm": True}, csrf=False).status_code, 403)
        response = self.post(browser, "billing/checkout/reset-test", {"confirm": True})
        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertEqual(order.status, "TEST_ARCHIVED")
        self.assertEqual(order.encrypted_payment_payload, "")
        self.assertTrue(PaymentEvent.objects.filter(order=order, processed_at__isnull=False).exists())
        self.assertEqual(browser.get("/api/v1/billing/checkout").status_code, 404)
        with patch("integrations.mercadopago.orders.payment") as provider:
            self.assertEqual(reconcile_payment(order.pk).status, "TEST_ARCHIVED")
        provider.assert_not_called()
        def new_provider(path, payload=None, key=None, **kwargs):
            result = self.provider(path, payload, key, **kwargs)
            if path == "/v1/orders":
                result["id"] = "ORDTST01M6M5MYRCKEXHNCSTPF06A5T7"
            return result
        with patch("integrations.mercadopago.orders.request_api", side_effect=new_provider):
            self.assertEqual(self.submit(browser, key="new-sandbox-attempt-002").status_code, 201)

    def test_provider_response_in_flight_cannot_activate_archived_test(self):
        from apps.billing.mercadopago import archive_sandbox_order
        _, order = self.create()
        def response(_):
            archive_sandbox_order(order.pk, order.session_digest)
            return self.snapshot(order)
        with patch("integrations.mercadopago.orders.payment", side_effect=response):
            self.assertEqual(reconcile_payment(order.pk).status, "TEST_ARCHIVED")
        self.assertFalse(Membership.objects.exists())

    def test_test_reset_blocks_production_other_session_and_confirmed_order(self):
        browser, order = self.create()
        other = self.browser()
        self.assertEqual(self.post(other, "billing/checkout/reset-test", {"confirm": True}).status_code, 404)
        with override_settings(MERCADOPAGO_ENVIRONMENT="production"):
            self.assertEqual(self.post(browser, "billing/checkout/reset-test", {"confirm": True}).status_code, 403)
        self.confirm(order)
        self.assertEqual(self.post(browser, "billing/checkout/reset-test", {"confirm": True}).status_code, 409)
        self.assertTrue(Membership.objects.exists())

    def test_refund_revokes_access_and_stops_future_renewal(self):
        _, order = self.create(); order = self.confirm(order)
        snapshot = self.snapshot(order, "refunded"); snapshot["transaction_amount_refunded"] = 699.90
        order = self.confirm(order, snapshot)
        self.assertEqual(order.status, "REVOKED")
        self.assertFalse(active_memberships(order.user).exists())
        self.assertIsNotNone(Subscription.objects.get().canceled_at)
        self.confirm(order, self.snapshot(order))
        self.assertFalse(active_memberships(order.user).exists())

    def test_cancellation_is_idempotent_and_keeps_paid_membership(self):
        _, order = self.create(); order = self.confirm(order)
        cancel_renewal(order.user); cancel_renewal(order.user)
        self.assertTrue(active_memberships(order.user).exists())
        Subscription.objects.update(next_charge_at=timezone.now() - timedelta(seconds=1))
        self.assertFalse(renew_due())

    def test_scheduler_never_creates_automatic_renewal(self):
        _, order = self.create(); order = self.confirm(order)
        Subscription.objects.update(status="ACTIVE", canceled_at=None, next_charge_at=timezone.now() - timedelta(seconds=1))
        with override_settings(MERCADOPAGO_AUTOMATIC_PAYMENTS_ENABLED=True):
            self.assertFalse(renew_due())
        self.assertEqual(Order.objects.count(), 1)

    def test_queued_renewal_is_canceled_without_provider_request(self):
        _, order = self.create()
        Order.objects.filter(pk=order.pk).update(cycle=1, provider_order_id=None)
        with patch("integrations.mercadopago.orders.request_api") as provider:
            result = send_order(order.pk)
        provider.assert_not_called()
        self.assertEqual(result.status, "CANCELED")

    def test_single_purchase_never_saves_card_or_creates_profile(self):
        _, order = self.create()
        payload = payment_payload(order, order.subscription, decode(order.subscription.encrypted_instrument), body()["card"])
        tx = payload["transactions"]["payments"][0]
        self.assertEqual(payload["payer"], {"email": "buyer@example.test"})
        self.assertEqual(tx["payment_method"]["installments"], 10)
        self.assertNotIn("stored_credential", tx)
        self.assertNotIn("automatic_payments", tx)
        order.cycle = 1
        with self.assertRaises(IdentityError): payment_payload(order, order.subscription, {}, body()["card"])

    def test_manual_new_purchase_is_allowed_after_paid_membership(self):
        _, order = self.create(); order = self.confirm(order)
        new = start_order(body(), "new-session", "manual-renewal-key")
        self.assertNotEqual(new.pk, order.pk)

    def signature(self, identifier="ORD01JS2V6CM8KJ0EC4H502TGK1WP", request_id="event-one"):
        manifest = f"id:{identifier};request-id:{request_id};ts:123456789;"
        return "ts=123456789,v1=" + hmac.new(b"synthetic-webhook", manifest.encode(), hashlib.sha256).hexdigest()

    def test_webhook_signature_tampering_and_repeated_event(self):
        browser, order = self.create()
        endpoint = "/api/v1/billing/mercadopago/webhook?data.id=ORD01JS2V6CM8KJ0EC4H502TGK1WP"
        payload = {"type": "order", "data": {"id": "ORD01JS2V6CM8KJ0EC4H502TGK1WP"}}
        self.assertEqual(browser.post(endpoint, payload, content_type="application/json").status_code, 403)
        with patch("integrations.mercadopago.orders.payment", return_value=self.snapshot(order)):
            for _ in range(2):
                response = browser.post(endpoint, payload, content_type="application/json",
                    HTTP_X_REQUEST_ID="event-one", HTTP_X_SIGNATURE=self.signature())
                self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(PaymentEvent.objects.count(), 2)  # envio + notificação deduplicada
        self.assertFalse(Membership.objects.exists())
        self.assertFalse(verify_signature("988", "event-one", self.signature()))
        self.assertFalse(verify_signature("ORD01JS2V6CM8KJ0EC4H502TGK1WP", "other", self.signature()))

    def test_status_endpoint_confirms_from_provider_not_browser(self):
        browser, order = self.create()
        with patch("integrations.mercadopago.orders.payment", return_value=self.snapshot(order, "pending")):
            response = browser.get("/api/v1/billing/checkout?status=approved")
            self.assertEqual(response.json()["status"], "WAITING")
        self.assertFalse(Membership.objects.exists())
        Order.objects.update(checked_at=None)
        with patch("integrations.mercadopago.orders.payment", return_value=self.snapshot(order)):
            self.assertEqual(browser.get("/api/v1/billing/checkout").json()["status"], "PAID")

    def test_cancel_requires_authenticated_owner_and_csrf(self):
        _, order = self.create(); order = self.confirm(order)
        browser = self.browser()
        self.assertIn(browser.get("/api/v1/billing/subscription").status_code, (401, 403))
        user = self.user(email="other@example.test")
        self.login(browser, user)
        self.assertIsNone(browser.get("/api/v1/billing/subscription").json()["subscription"])
        self.assertEqual(self.post(browser, "billing/subscription", {"cancelRenewal": True}, csrf=False).status_code, 403)
        self.assertEqual(self.post(browser, "billing/subscription", {"cancelRenewal": True}).status_code, 200)
        self.assertIsNotNone(Subscription.objects.get().canceled_at)

    def test_transport_refuses_writes_during_configuration_checks(self):
        with self.assertRaises(ValueError):
            request_api("/v1/orders", {}, configuration_check=True)


    def test_native_cancellation_uses_bearer_and_cannot_use_browser_cookie(self):
        from apps.identity.models import MobileSession
        from apps.identity.security import digest
        _, order = self.create(); order = self.confirm(order)
        order.user.email_verified_at = timezone.now()
        order.user.save(update_fields=["email_verified_at"])
        token = "x" * 43
        MobileSession.objects.create(pk=digest(token), user=order.user, auth_version=order.user.auth_version,
            expires_at=timezone.now() + timedelta(hours=1), last_active_at=timezone.now())
        browser = self.browser()
        endpoint = "/api/v1/mobile/billing/subscription"
        self.assertEqual(browser.get(endpoint).status_code, 401)
        result = browser.get(endpoint, HTTP_AUTHORIZATION="Bearer " + token)
        self.assertEqual(result.status_code, 200, result.content)
        result = browser.post(endpoint, {"cancelRenewal": True}, content_type="application/json", HTTP_AUTHORIZATION="Bearer " + token)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertTrue(active_memberships(order.user).exists())


    def test_expired_uncertain_payment_is_not_resent_and_requires_review(self):
        browser = self.browser()
        def fail(path, payload=None, key=None, **kwargs):
            if path == "/v1/orders":
                raise IdentityError("TIMEOUT", "Timeout", 503)
            return self.provider(path, payload, key)
        with patch("integrations.mercadopago.orders.request_api", side_effect=fail):
            self.assertEqual(self.submit(browser).status_code, 503)
        order = Order.objects.get()
        Order.objects.filter(pk=order.pk).update(payment_started_at=timezone.now() - timedelta(days=1))
        with patch("integrations.mercadopago.orders.request_api") as provider, self.assertRaises(IdentityError):
            send_order(order.pk)
        provider.assert_not_called()
        self.assertEqual(Subscription.objects.get().status, "REVIEW")
        order.refresh_from_db()
        self.assertEqual(order.encrypted_payment_payload, "")
        with patch("integrations.mercadopago.orders.request_api") as provider:
            self.assertEqual(send_order(order.pk).status, "REVIEW")
            provider.assert_not_called()

    def test_wrong_receiving_account_blocks_before_any_charge(self):
        def wrong(path, payload=None, key=None, **kwargs):
            result = self.provider(path, payload, key)
            if path == "/users/me":
                result["id"] = 999
            return result
        with patch("integrations.mercadopago.orders.request_api", side_effect=wrong) as provider:
            self.assertEqual(self.submit(self.browser()).status_code, 422)
        self.assertFalse(any(call.args[0] == "/v1/orders" for call in provider.call_args_list))


    def test_refund_is_processed_even_when_new_sales_are_disabled(self):
        _, order = self.create(); order = self.confirm(order)
        snapshot = self.snapshot(order, "refunded")
        PaymentEvent.objects.create(digest="r" * 64, order=order, provider_order_id=order.provider_order_id, available_at=timezone.now())
        with override_settings(BILLING_ENABLED=False), patch("integrations.mercadopago.orders.payment", return_value=snapshot):
            self.assertTrue(process_payment())
        order.refresh_from_db()
        self.assertEqual(order.status, "REVOKED")

    def test_orders_raw_snapshot_activates_and_partial_refund_revokes(self):
        from integrations.mercadopago.orders import normalize
        from .test_mercadopago_orders import snapshot
        _, order = self.create()
        raw = snapshot(); raw["external_reference"] = str(order.pk)
        raw["last_updated_date"] = timezone.now().isoformat()
        order = self.confirm(order, normalize(raw))
        self.assertEqual(order.status, "PAID")
        raw["transactions"]["payments"][0]["status_detail"] = "partially_refunded"
        order = self.confirm(order, normalize(raw))
        self.assertEqual(order.status, "REVOKED")
        self.assertFalse(active_memberships(order.user).exists())
