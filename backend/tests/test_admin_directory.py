from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.billing.models import Membership, Order
from apps.billing.provider import environment
from apps.identity.models import User
from .test_identity import IdentityTests


class AdminDirectoryTests(TestCase):
    browser = IdentityTests.browser
    post = IdentityTests.post
    user = IdentityTests.user
    login = IdentityTests.login
    team_login = IdentityTests.team_login

    def setUp(self):
        self.admin, self.admin_user, *_ = self.team_login()
        self.client_user = self.user(email="client@example.test")
        self.lawyer = self.user(email="lawyer@example.test", role="LAWYER")
        self.pending = self.user(email="pending@example.test", role="LAWYER")
        self.pending.email_verified_at = None
        self.pending.save()
        self.revoked = self.user(email="revoked@example.test")
        self.revoked.is_active = False
        self.revoked.save()

    def test_includes_clients_and_global_counts_independent_of_filters(self):
        data = self.admin.get("/api/v1/admin/users?role=CLIENT&status=active&search=CLIENT@").json()
        self.assertEqual([row["id"] for row in data["results"]], [str(self.client_user.pk)])
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["summary"], {"total": 5, "lawyers": 1, "clients": 1, "pending": 1, "revoked": 1})
        pending = self.admin.get("/api/v1/admin/users?status=pending").json()
        self.assertEqual([row["id"] for row in pending["results"]], [str(self.pending.pk)])
        revoked = self.admin.get("/api/v1/admin/users?status=revoked").json()
        self.assertEqual([row["id"] for row in revoked["results"]], [str(self.revoked.pk)])

    def test_counts_cover_all_pages_and_cursor_preserves_filter(self):
        for number in range(23):
            self.user(email=f"client{number}@example.test")
        first = self.admin.get("/api/v1/admin/users?role=CLIENT").json()
        self.assertEqual(first["total"], 25)
        self.assertEqual(len(first["results"]), 20)
        second = self.admin.get("/api/v1/admin/users", {"role": "CLIENT", "cursor": first["nextCursor"]}).json()
        self.assertEqual(len(second["results"]), 5)
        self.assertEqual(second["summary"]["clients"], 24)
        self.assertFalse(set(row["id"] for row in first["results"]) & set(row["id"] for row in second["results"]))

    def test_only_admin_can_read_directory_and_invalid_filters_fail(self):
        client = self.browser()
        self.login(client, self.client_user)
        self.assertEqual(client.get("/api/v1/admin/users").status_code, 403)
        lawyer, _, *_ = self.team_login("LAWYER", "otherlawyer@example.test")
        self.assertEqual(lawyer.get("/api/v1/admin/users").status_code, 403)
        for params in ({"role": "ROOT"}, {"status": "unknown"}, {"search": "x" * 151}):
            self.assertEqual(self.admin.get("/api/v1/admin/users", params).status_code, 400)

    def test_details_show_membership_and_isolated_access_history(self):
        now = timezone.now()
        order = Order.objects.create(request_key="details-test", session_digest="synthetic", amount=10000,
            environment=environment(), policy_version="test", status="PAID", user=self.client_user)
        membership = Membership.objects.create(order=order, user=self.client_user,
            starts_at=now-timedelta(days=1), expires_at=now+timedelta(days=30))
        path = f"/api/v1/admin/users/{self.client_user.pk}/details"
        self.assertEqual(self.admin.get(path).json()["membership"]["status"], "ACTIVE")
        self.post(self.admin, f"admin/users/{self.client_user.pk}/access", {
            "active": False, "version": 1, "reason": "Revisão administrativa solicitada"})
        result = self.admin.get(path).json()
        self.assertFalse(result["user"]["active"])
        self.assertEqual(result["membership"]["status"], "ACTIVE")
        self.assertEqual(result["results"][0]["actor"], self.admin_user.email)
        self.assertEqual(result["results"][0]["reason"], "Revisão administrativa solicitada")
        self.assertEqual(self.admin.get(f"/api/v1/admin/users/{self.lawyer.pk}/details").json()["results"], [])
        membership.expires_at = now-timedelta(hours=1)
        membership.save()
        self.assertEqual(self.admin.get(path).json()["membership"]["status"], "EXPIRED")
        membership.revoked_at = now
        membership.save()
        self.assertEqual(self.admin.get(path).json()["membership"]["status"], "REVOKED")
        order.environment = "other"
        order.save()
        self.assertEqual(self.admin.get(path).json()["membership"]["status"], "NONE")

    def test_details_denied_to_other_profiles(self):
        client = self.browser()
        self.login(client, self.client_user)
        path = f"/api/v1/admin/users/{self.client_user.pk}/details"
        self.assertEqual(client.get(path).status_code, 403)
        lawyer, _, *_ = self.team_login("LAWYER", "detailslawyer@example.test")
        self.assertEqual(lawyer.get(path).status_code, 403)
