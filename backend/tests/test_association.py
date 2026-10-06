import base64
import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.billing.models import Order, Membership, PaymentEvent
from apps.billing.services import reconcile, active_memberships
from apps.cases.models import Case, ServiceAccess
from apps.cases.services import submission_access
from apps.communication.models import Notification, CaseEmail
from apps.documents.models import Document, DocumentVersion
from apps.identity.models import User, IdentityEmail, ActionToken
from apps.identity.security import IdentityError
from integrations.pagbank.client import create_checkout, verify_signature
from jobs.billing import process_payment
from .test_identity import IdentityTests, PASSWORD


@override_settings(MEMBERSHIP_REQUIRED=True, CASE_AUTO_ASSIGN=True, CASE_INTAKE_REQUIRED=True,
    IDENTITY_SHARED_PORTAL=True, IDENTITY_MFA_REQUIRED=False,
    BILLING_ENABLED=True, PAGBANK_ENVIRONMENT="sandbox",
    PORTAL_ORIGINS={"client": "http://localhost:3000", "team": "http://localhost:3000"})
class AssociationTests(TestCase):
    browser = IdentityTests.browser
    post = IdentityTests.post
    user = IdentityTests.user
    login = IdentityTests.login
    email_token = IdentityTests.email_token

    def order(self):
        return Order.objects.create(request_key=uuid4().hex, session_digest=uuid4().hex, amount=79799,
            environment="sandbox", policy_version="development-v1", checkout_id="CHEC_" + uuid4().hex)

    def snapshot(self, order, email="buyer@example.test", status="PAID"):
        return {"id": "ORDE_" + uuid4().hex, "reference_id": str(order.pk),
            "items": [{"reference_id": "iustus-associacao-anual", "quantity": 1, "unit_amount": 79799}],
            "customer": {"email": email, "name": "Associado Teste"},
            "charges": [{"id": "CHAR_test", "status": status, "paid_at": timezone.now().isoformat(),
                "amount": {"value": 79799, "currency": "BRL", "summary": {"paid": 79799 if status == "PAID" else 0, "refunded": 0}}}]}

    def confirm(self, order, snapshot=None):
        data = snapshot or self.snapshot(order)
        with patch("apps.billing.services.request_api", return_value=data):
            return reconcile(order.pk, data["id"])

    def activate(self):
        order = self.confirm(self.order())
        browser = self.browser()
        token = self.email_token("member")
        result = self.post(browser, "billing/activate", {"token": token, "name": "Associado Teste", "password": PASSWORD})
        self.assertEqual(result.status_code, 204, result.content)
        self.assertEqual(self.login(browser, order.user).status_code, 200)
        return browser, order.user

    def document(self, case, user, status="AVAILABLE"):
        return DocumentVersion.objects.create(document=Document.objects.create(case=case, created_by=user),
            uploaded_by=user, number=1, filename="prova.pdf", declared_mime="application/pdf", size_bytes=20,
            object_key=uuid4().hex, status=status, expires_at=timezone.now() + timedelta(hours=1))

    def submit(self, browser, case):
        csrf = browser.get("/api/v1/auth/csrf").json()["csrfToken"]
        return browser.post(f"/api/v1/cases/{case.pk}/submit", {"version": case.version}, content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf, HTTP_IDEMPOTENCY_KEY="submit-" + str(case.pk))

    def draft(self, user):
        return Case.objects.create(owner=user, title="Ocorrência", description="Relato detalhado da ocorrência para análise.",
            category="CONSUMER", occurred_on=timezone.localdate(), scope_acknowledged=True)

    def test_public_registration_and_manual_grant_do_not_replace_payment(self):
        browser = self.browser()
        self.assertFalse(browser.get("/api/v1/auth/csrf").json()["registrationAvailable"])
        self.assertEqual(self.post(browser, "auth/register", {}).status_code, 403)
        user, admin = self.user(), self.user(role="ADMIN", email="admin@example.test")
        ServiceAccess.objects.create(user=user, granted_by=admin, enabled=True, reason="Legacy", expires_at=timezone.now()+timedelta(days=1))
        self.assertFalse(submission_access(user)["canSubmit"])

    def test_waiting_declined_and_checkout_return_never_activate(self):
        order = self.order()
        for status in ["WAITING", "IN_ANALYSIS", "DECLINED"]:
            self.confirm(order, self.snapshot(order, status=status) | {"id": "ORDE_one"})
            self.assertFalse(Membership.objects.exists())
            self.assertFalse(User.objects.exists())
        self.assertEqual(self.browser().get("/api/v1/billing/checkout").status_code, 404)

    def test_paid_order_is_idempotent_and_activation_is_single_use(self):
        order, browser = self.order(), self.browser()
        snapshot = self.snapshot(order)
        self.confirm(order, snapshot)
        token = self.email_token("member")
        self.confirm(order, snapshot)
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(IdentityEmail.objects.count(), 1)
        user = User.objects.get()
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.login(browser, user).status_code, 403)
        body = {"token": token, "name": "Associado Teste", "password": PASSWORD}
        self.assertEqual(self.post(browser, "billing/activate", body).status_code, 204)
        self.assertEqual(self.post(browser, "billing/activate", body).status_code, 400)
        self.assertEqual(self.login(browser, user).status_code, 200)
        self.assertTrue(submission_access(user)["canSubmit"])

    def test_existing_account_password_and_identity_are_preserved(self):
        user = self.user(email="buyer@example.test")
        old = user.password
        order = self.confirm(self.order())
        user.refresh_from_db()
        self.assertEqual(user.password, old)
        self.assertEqual(order.user_id, user.pk)
        self.assertFalse(ActionToken.objects.filter(purpose="MEMBER").exists())
        self.assertEqual(IdentityEmail.objects.count(), 1)

    def test_price_reference_currency_and_buyer_are_validated(self):
        for mutation in ["reference", "price", "currency", "email", "date"]:
            order = self.order()
            data = self.snapshot(order)
            if mutation == "reference": data["reference_id"] = str(uuid4())
            if mutation == "price": data["items"][0]["unit_amount"] = 1
            if mutation == "currency": data["charges"][0]["amount"]["currency"] = "USD"
            if mutation == "email": data["customer"]["email"] = "invalid"
            if mutation == "date": data["charges"][0]["paid_at"] = "invalid"
            try:
                self.confirm(order, data)
            except IdentityError:
                pass
            self.assertFalse(Membership.objects.filter(order=order).exists(), mutation)

    def test_environment_mismatch_and_staff_buyers_are_not_granted(self):
        order = self.order()
        order.environment = "production"; order.save()
        with self.assertRaises(IdentityError): self.confirm(order)
        self.user(role="ADMIN", email="buyer@example.test")
        with self.assertRaises(IdentityError): self.confirm(self.order())
        self.assertFalse(Membership.objects.exists())

    def test_refund_revokes_new_submissions_without_deleting_cases(self):
        browser, user = self.activate()
        case = self.draft(user)
        order = Order.objects.get(user=user)
        data = self.snapshot(order) | {"id": order.provider_order_id}
        data["charges"][0]["amount"]["summary"]["refunded"] = 79799
        self.confirm(order, data)
        self.assertFalse(submission_access(user)["canSubmit"])
        self.assertEqual(browser.get(f"/api/v1/cases/{case.pk}").status_code, 200)
        # Mesmo um snapshot antigo PAID não reativa um pedido já revogado.
        self.confirm(order, self.snapshot(order) | {"id": order.provider_order_id})
        self.assertFalse(active_memberships(user).exists())

    def test_expiration_blocks_new_cases_and_renewal_extends_period(self):
        first = self.confirm(self.order())
        end = Membership.objects.get(order=first).expires_at
        second = self.confirm(self.order())
        renewed = Membership.objects.get(order=second)
        self.assertEqual(renewed.starts_at, end)
        self.assertEqual(renewed.expires_at.year, end.year + 1)
        Membership.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertFalse(submission_access(first.user)["canSubmit"])

    def test_checkout_is_session_scoped_and_retries_keep_reference(self):
        browser = self.browser()
        csrf = browser.get("/api/v1/auth/csrf").json()["csrfToken"]
        def create():
            return browser.post("/api/v1/billing/checkout", {"accepted": True}, content_type="application/json",
                HTTP_X_CSRFTOKEN=csrf, HTTP_IDEMPOTENCY_KEY="synthetic-checkout-001")
        with patch("apps.billing.views.create_checkout", side_effect=IdentityError("PROVIDER", "Timeout", 503)):
            self.assertEqual(create().status_code, 503)
        original = Order.objects.get().pk
        with patch("apps.billing.views.create_checkout", return_value=("CHEC_test", "https://pagamento.pagbank.com.br/test")) as provider:
            self.assertEqual(create().status_code, 201)
            self.assertEqual(create().status_code, 201)
            self.assertEqual(provider.call_count, 1)
        self.assertEqual(Order.objects.get().pk, original)
        self.assertEqual(Order.objects.get().amount, 95880)
        self.assertEqual(browser.get("/api/v1/billing/plan").json()["amount"], 95880)
        self.assertEqual(browser.get("/api/v1/billing/checkout").json()["status"], "WAITING")
        self.assertEqual(self.browser().get("/api/v1/billing/checkout").status_code, 404)

    def test_checkout_payload_uses_server_price_and_validates_redirect(self):
        order = self.order()
        with patch("integrations.pagbank.client.request_api", return_value={"id": "CHEC_test", "links": [{"rel": "PAY", "href": "https://pagamento.pagbank.com.br/test"}]}) as provider:
            create_checkout(order)
            data = provider.call_args.args[1]
            self.assertEqual(data["items"][0]["unit_amount"], 79799)
            self.assertIn("billing/webhook", data["payment_notification_urls"][0])
            self.assertEqual(data["payment_methods_configs"], [{"type": "CREDIT_CARD", "config_options": [
                {"option": "INSTALLMENTS_LIMIT", "value": "12"},
                {"option": "INTEREST_FREE_INSTALLMENTS", "value": "12"},
            ]}])
        for url in ["https://pagamento.pagbank.com.br.evil.test", "http://pagbank.com.br", "https://evil.test"]:
            with patch("integrations.pagbank.client.request_api", return_value={"id": "CHEC_test", "links": [{"rel": "PAY", "href": url}]}):
                with self.assertRaises(IdentityError): create_checkout(order)

    def test_signed_webhook_is_deduplicated_and_worker_confirms_current_state(self):
        order = self.order()
        data = self.snapshot(order)
        raw = json.dumps(data).encode()
        key = ec.generate_private_key(ec.SECP256R1())
        public = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
        signature = base64.b64encode(key.sign(raw, ec.ECDSA(hashes.SHA256()))).decode()
        browser = self.browser()
        with override_settings(PAGBANK_WEBHOOK_PUBLIC_KEY=public):
            self.assertFalse(verify_signature(raw + b" ", signature))
            self.assertTrue(verify_signature(raw, "invalid," + signature))
            self.assertEqual(browser.post("/api/v1/billing/webhook", raw, content_type="application/json").status_code, 403)
            for _ in range(2):
                self.assertEqual(browser.post("/api/v1/billing/webhook", raw, content_type="application/json", HTTP_X_PAYLOAD_SIGNATURE=signature).status_code, 204)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertFalse(Membership.objects.exists())
        with patch("apps.billing.services.request_api", return_value=data):
            self.assertTrue(process_payment())
        self.assertTrue(Membership.objects.exists())
        self.assertFalse(process_payment())

    def test_worker_retries_provider_failure_without_granting_access(self):
        event = PaymentEvent.objects.create(digest="event", order=self.order(), provider_order_id="ORDE_test", available_at=timezone.now())
        with patch("apps.billing.services.request_api", side_effect=RuntimeError("unavailable")):
            self.assertTrue(process_payment())
        event.refresh_from_db()
        self.assertEqual(event.attempts, 1)
        self.assertIsNone(event.processed_at)
        self.assertGreater(event.available_at, timezone.now())
        self.assertFalse(Membership.objects.exists())

    def test_intake_requires_date_and_verified_evidence_from_same_case(self):
        browser, user = self.activate()
        case = self.draft(user)
        case.occurred_on = None; case.save()
        self.assertEqual(self.submit(browser, case).json()["error"]["code"], "OCCURRENCE_DATE_REQUIRED")
        case.occurred_on = timezone.localdate(); case.save()
        self.document(self.draft(user), user)
        evidence = self.document(case, user, "QUARANTINED")
        self.assertEqual(self.submit(browser, case).json()["error"]["code"], "EVIDENCE_REQUIRED")
        evidence.status = "AVAILABLE"; evidence.save()
        self.assertEqual(self.submit(browser, case).status_code, 200)
        future = self.post(browser, "cases", {"occurredOn": (timezone.localdate()+timedelta(days=1)).isoformat()})
        self.assertEqual(future.status_code, 400)

    def test_auto_assignment_balances_and_notifies_both_parties(self):
        browser, user = self.activate()
        lawyers = [self.user(role="LAWYER", email=f"lawyer{i}@example.test") for i in range(2)]
        assigned = []
        for _ in range(2):
            case = self.draft(user); self.document(case, user)
            response = self.submit(browser, case)
            self.assertEqual(response.status_code, 200, response.content)
            case.refresh_from_db(); assigned.append(case.lawyer_id)
            self.assertEqual(Notification.objects.filter(case=case, kind="ASSIGNED", recipient=case.lawyer).count(), 1)
            self.assertEqual(Notification.objects.filter(case=case, kind="SUBMITTED", recipient=user).count(), 1)
            self.assertEqual(CaseEmail.objects.filter(notification__case=case).count(), 2)
        self.assertEqual(set(assigned), {lawyer.pk for lawyer in lawyers})

    def test_no_lawyer_falls_back_to_administrative_queue(self):
        browser, user = self.activate()
        admin = self.user(role="ADMIN", email="admin@example.test")
        case = self.draft(user); self.document(case, user)
        self.assertEqual(self.submit(browser, case).status_code, 200)
        case.refresh_from_db(); self.assertIsNone(case.lawyer_id)
        self.assertTrue(Notification.objects.filter(recipient=admin, kind="UNASSIGNED").exists())

    def test_approved_case_has_its_own_mandate_and_cannot_skip_signature(self):
        browser, user = self.activate()
        lawyer = self.user(role="LAWYER", email="lawyer@example.test")
        team = self.browser(); self.login(team, lawyer)
        case = self.draft(user); self.document(case, user)
        self.assertEqual(self.submit(browser, case).status_code, 200)
        case.refresh_from_db()
        def act(route, **data):
            case.refresh_from_db()
            return self.post(team, f"cases/{case.pk}/{route}", {"version": case.version, **data})
        self.assertEqual(act("transitions", targetState="EM_TRIAGEM").status_code, 200)
        self.assertEqual(act("transitions", targetState="ACEITO", reason="Análise concluída", scopeConfirmed=True, conflictChecked=True, informationSufficient=True).status_code, 200)
        foreign = self.document(self.draft(user), lawyer)
        self.assertEqual(act("workflow", action="START", text="Atendimento específico desta ocorrência", position="AUTHOR", documentId=str(foreign.pk)).status_code, 422)
        mandate = self.document(case, lawyer)
        self.assertEqual(act("workflow", action="START", text="Atendimento específico desta ocorrência", position="AUTHOR", documentId=str(mandate.pk)).status_code, 200)
        self.assertTrue(Notification.objects.filter(case=case, recipient=user, kind="LEGAL_START").exists())
        self.assertEqual(act("workflow", action="VERIFY", confirmed=True).status_code, 422)
        signed = self.document(case, user)
        case.refresh_from_db()
        self.assertEqual(self.post(browser, f"cases/{case.pk}/workflow", {"version": case.version, "action": "SIGN", "documentId": str(signed.pk)}).status_code, 200)
        self.assertEqual(act("workflow", action="VERIFY", confirmed=True).status_code, 200)
        case.refresh_from_db(); self.assertEqual(case.state, "EM_PREPARACAO")
