from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4
from django.db import connection, connections, transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from apps.billing.models import Order, Membership
from apps.billing.services import reconcile
from apps.identity.models import User, IdentityEmail
from apps.cases.models import Case
from apps.cases.services import assign_automatically


@skipUnless(connection.vendor == "postgresql", "Exige locks reais de PostgreSQL")
@override_settings(PAGBANK_ENVIRONMENT="sandbox", IDENTITY_MFA_REQUIRED=False)
class AssociationConcurrencyTests(TransactionTestCase):
    def test_duplicate_confirmations_create_one_membership_and_one_email(self):
        order = Order.objects.create(request_key=uuid4().hex, session_digest=uuid4().hex, amount=79799, environment="sandbox", policy_version="test")
        snapshot = {"id": "ORDE_parallel", "reference_id": str(order.pk),
            "items": [{"reference_id": "iustus-associacao-anual", "quantity": 1, "unit_amount": 79799}],
            "customer": {"email": "parallel@example.test", "name": "Associado Sintético"},
            "charges": [{"status": "PAID", "paid_at": timezone.now().isoformat(), "amount": {"currency": "BRL", "value": 79799, "summary": {"paid": 79799, "refunded": 0}}}]}
        barrier = Barrier(2)
        def confirm(_):
            try:
                barrier.wait(timeout=10)
                return reconcile(order.pk, "ORDE_parallel").status
            finally:
                connections.close_all()
        with patch("apps.billing.services.request_api", return_value=snapshot):
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(list(pool.map(confirm, range(2))), ["PAID", "PAID"])
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(IdentityEmail.objects.count(), 1)

    def test_simultaneous_cases_are_distributed_without_racing_counts(self):
        owner = User.objects.create_user("owner@example.test")
        lawyers = [User.objects.create_user(f"lawyer{i}@example.test", role="LAWYER", email_verified_at=timezone.now()) for i in range(2)]
        cases = [Case.objects.create(owner=owner, state="SUBMETIDO") for _ in range(2)]
        barrier = Barrier(2)
        def assign(index):
            try:
                barrier.wait(timeout=10)
                with transaction.atomic():
                    item = Case.objects.select_for_update().get(pk=cases[index].pk)
                    assign_automatically(item)
                    return item.lawyer_id
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(set(pool.map(assign, range(2))), {row.pk for row in lawyers})
