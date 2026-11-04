from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
from django.db import connection, connections
from django.test import TransactionTestCase, override_settings
from apps.billing.mercadopago import start_order, send_order, reconcile_payment
from apps.billing.models import Order, Membership
from apps.identity.models import IdentityEmail
from . import test_mercadopago as fixtures


@skipUnless(connection.vendor == "postgresql", "Exige locks reais de PostgreSQL")
@override_settings(**fixtures.CONFIG)
class MercadoPagoConcurrencyTests(TransactionTestCase):
    provider = fixtures.MercadoPagoTests.provider
    snapshot = fixtures.MercadoPagoTests.snapshot

    def parallel(self, operation):
        barrier = Barrier(2)
        def run(_):
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, range(2)))

    def test_simultaneous_sends_charge_once(self):
        order = start_order(fixtures.body(), "session", "synthetic-concurrent-key")
        with patch("integrations.mercadopago.orders.request_api", side_effect=self.provider) as provider:
            statuses = self.parallel(lambda: send_order(order.pk, fixtures.body()["card"]).status)
        self.assertEqual(statuses, ["WAITING", "WAITING"])
        self.assertEqual(len([call for call in provider.call_args_list if call.args[0] == "/v1/orders"]), 1)

    def test_simultaneous_confirmations_activate_once(self):
        order = start_order(fixtures.body(), "session", "synthetic-concurrent-key")
        with patch("integrations.mercadopago.orders.request_api", side_effect=self.provider):
            order = send_order(order.pk, fixtures.body()["card"])
        with patch("integrations.mercadopago.orders.payment", return_value=self.snapshot(order)):
            self.assertEqual(self.parallel(lambda: reconcile_payment(order.pk, "ORD01JS2V6CM8KJ0EC4H502TGK1WP").status), ["PAID", "PAID"])
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(IdentityEmail.objects.count(), 1)
