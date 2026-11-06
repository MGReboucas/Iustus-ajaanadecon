import io
import json
from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.billing.models import Membership, Order
from apps.billing.services import send_access
from apps.identity.models import IdentityEmail, User
from apps.identity.security import encrypt
from apps.privacy.models import PrivacyRequest
from jobs.mail import deliver_one
from jobs.mail_health import update_mail_health
from jobs.transactional_mail import notify_payment, notify_privacy, schedule_membership_notices
from apps.cases.models import Case
from apps.communication.services import EVENT_TITLES, create_notice
from jobs.communication import deliver_case_email, schedule_reminders
from apps.legal.models import LegalTask


@override_settings(BILLING_PROVIDER="pagbank", PAGBANK_ENVIRONMENT="sandbox")
class MailLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("synthetic@example.test", None)
        self.order = Order.objects.create(user=self.user, request_key=uuid4().hex,
            session_digest=uuid4().hex, amount=69990, environment="sandbox", policy_version="test",
            status="PAID", encrypted_customer=encrypt(json.dumps({"email": self.user.email})))
        self.membership = Membership.objects.create(user=self.user, order=self.order,
            starts_at=timezone.now()-timedelta(days=360), expires_at=timezone.now()+timedelta(days=5))

    def test_resend_only_delivers_latest_member_link(self):
        send_access(self.user)
        old = IdentityEmail.objects.get()
        send_access(self.user)
        deliver_one()
        old.refresh_from_db()
        self.assertIsNotNone(old.cancelled_at)
        self.assertEqual(old.encrypted_body, "")
        self.assertEqual(len(mail.outbox), 0)
        deliver_one()
        self.assertEqual(len(mail.outbox), 1)

    def test_refund_cancels_queued_member_and_plain_activation(self):
        for verified in (False, True):
            with self.subTest(verified=verified):
                self.membership.revoked_at = None
                self.membership.save()
                if verified:
                    self.user.email_verified_at = timezone.now()
                    self.user.set_password("synthetic-password")
                    self.user.save()
                send_access(self.user)
                self.membership.revoked_at = timezone.now()
                self.membership.save()
                deliver_one()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(IdentityEmail.objects.filter(cancelled_at__isnull=False).count(), 2)

    def test_payment_notices_are_idempotent_and_revalidate_status(self):
        self.order.status = "DECLINED"
        self.order.save()
        notify_payment(self.order)
        notify_payment(self.order)
        self.assertEqual(IdentityEmail.objects.count(), 1)
        self.order.status = "PAID"
        self.order.save()
        deliver_one()
        self.assertEqual(len(mail.outbox), 0)
        self.order.status = "REVOKED"
        self.order.save()
        notify_payment(self.order)
        deliver_one()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reversão", mail.outbox[0].body)

    def test_new_buyer_receives_decline_without_account(self):
        self.order.user = None
        self.order.status = "DECLINED"
        self.order.save()
        notify_payment(self.order)
        deliver_one()
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_expiry_is_deduplicated_and_renewal_cancels_old_warning(self):
        schedule_membership_notices()
        schedule_membership_notices()
        self.assertEqual(IdentityEmail.objects.count(), 1)
        self.membership.expires_at += timedelta(days=365)
        self.membership.save()
        deliver_one()
        self.assertEqual(len(mail.outbox), 0)

    def test_expired_association_notice_and_environment_isolation(self):
        self.membership.expires_at = timezone.now()-timedelta(days=1)
        self.membership.save()
        with override_settings(PAGBANK_ENVIRONMENT="production"):
            schedule_membership_notices()
        self.assertEqual(IdentityEmail.objects.count(), 0)
        schedule_membership_notices()
        deliver_one()
        self.assertIn("terminou", mail.outbox[0].body)

    def test_privacy_notices_do_not_expose_request_or_response(self):
        request = PrivacyRequest.objects.create(owner=self.user, kind="ACCESS", description="PRIVATE REQUEST")
        notify_privacy(request)
        request.status, request.response = "ANSWERED", "PRIVATE RESPONSE"
        request.save()
        notify_privacy(request)
        notify_privacy(request)
        deliver_one()
        deliver_one()
        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertNotIn("PRIVATE", message.body)

    def test_exhausted_mail_requires_explicit_retry_and_keeps_validation(self):
        send_access(self.user)
        item = IdentityEmail.objects.get()
        IdentityEmail.objects.update(attempts=4)
        with patch("jobs.mail.build_message", side_effect=ConnectionError), self.assertLogs("jobs.mail", level="CRITICAL"):
            deliver_one()
        self.assertFalse(deliver_one())
        call_command("retry_mail", "identity", str(item.pk), stdout=io.StringIO())
        self.membership.revoked_at = timezone.now()
        self.membership.save()
        deliver_one()
        item.refresh_from_db()
        self.assertIsNotNone(item.cancelled_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_strict_health_requires_heartbeat_and_healthy_queue(self):
        with self.assertRaises(CommandError):
            call_command("check_mail", strict=True, stdout=io.StringIO())
        update_mail_health()
        call_command("check_mail", strict=True, stdout=io.StringIO())
        send_access(self.user)
        IdentityEmail.objects.update(attempts=5)
        with self.assertRaises(CommandError):
            call_command("check_mail", strict=True, stdout=io.StringIO())

    def test_case_event_templates_are_specific_and_do_not_expose_case_details(self):
        self.user.email_verified_at = timezone.now()
        self.user.save()
        case = Case.objects.create(owner=self.user, state=Case.State.TRACKING, title="PRIVATE CASE")
        for kind, title in EVENT_TITLES.items():
            if kind in ("TASK_REMINDER", "TASK_OVERDUE"):
                continue
            create_notice(recipient_id=self.user.pk, source_key=kind, case=case, kind=kind, title="PRIVATE EVENT")
            self.assertTrue(deliver_case_email())
            message = mail.outbox[-1]
            self.assertIn(title, message.body)
            self.assertNotIn("PRIVATE", message.body)
            self.assertIn("/cliente", message.body)

    def test_overdue_escalation_is_once_and_only_to_lawyer(self):
        from apps.communication.models import Notification
        lawyer = User.objects.create_user("lawyer@example.test", None, role="LAWYER", email_verified_at=timezone.now())
        case = Case.objects.create(owner=self.user, lawyer=lawyer, state=Case.State.TRACKING)
        LegalTask.objects.create(case=case, kind="HEARING", title="PRIVATE TASK", due_at=timezone.now()-timedelta(days=2))
        schedule_reminders()
        schedule_reminders()
        overdue = Notification.objects.get(kind="TASK_OVERDUE")
        self.assertEqual(overdue.recipient_id, lawyer.pk)
