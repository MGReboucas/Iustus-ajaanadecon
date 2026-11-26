from django.core import mail
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from apps.cases.models import Case, CaseEvent
from apps.cases.services import changed
from apps.communication.models import CaseEmail, Notification
from apps.communication.services import notify_event
from apps.identity.models import User
from jobs.communication import deliver_case_email


class EventMailCoverageTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('client@example.test', None, email_verified_at=timezone.now())
        self.lawyer = User.objects.create_user('lawyer@example.test', None, role='LAWYER', email_verified_at=timezone.now())
        self.case = Case.objects.create(owner=self.owner, lawyer=self.lawyer, state=Case.State.TRACKING)

    def deliver_event(self, action, actor, recipients, public=True):
        before = len(mail.outbox)
        with transaction.atomic():
            changed(self.case, actor, action, 'PRIVATE EVENT CONTENT', public=public)
        event = CaseEvent.objects.latest('created_at')
        notify_event(event, self.case)
        while deliver_case_email():
            pass
        messages = mail.outbox[before:]
        self.assertCountEqual([message.to[0] for message in messages], recipients)
        for message in messages:
            self.assertNotIn('PRIVATE EVENT CONTENT', message.body)
        self.assertFalse(CaseEmail.objects.filter(sent_at__isnull=True).exists())

    def test_every_public_legal_movement_reaches_client(self):
        for action in ('TRIAGE_STARTED', 'TRIAGE_DECISION', 'INFORMATION_REQUESTED',
                       'INFORMATION_RESOLVED', 'PROPOSAL_PUBLISHED',
                       'LEGAL_START', 'LEGAL_RETURN_MANDATE', 'LEGAL_VERIFY', 'LEGAL_PUBLISH',
                       'LEGAL_FILE', 'LEGAL_TASK', 'LEGAL_RESCHEDULE', 'LEGAL_COMPLETE',
                       'LEGAL_UPDATE', 'LEGAL_CLOSE'):
            with self.subTest(action=action):
                self.deliver_event(action, self.lawyer, [self.owner.email])

    def test_client_responses_reach_responsible_lawyer(self):
        for action in ('INFORMATION_RESPONDED', 'PROPOSAL_ACCEPTED', 'PROPOSAL_DECLINED', 'LEGAL_SIGN'):
            with self.subTest(action=action):
                self.deliver_event(action, self.owner, [self.lawyer.email])

    def test_document_lifecycle_never_sends_email(self):
        for action in ('DOCUMENT_UPLOAD_STARTED', 'DOCUMENT_QUARANTINED', 'DOCUMENT_DEMO_RECEIVED',
                       'DOCUMENT_AVAILABLE', 'DOCUMENT_REJECTED'):
            with self.subTest(action=action):
                self.deliver_event(action, self.owner, [])
        self.assertFalse(Notification.objects.filter(kind__startswith='DOCUMENT_').exists())

    def test_drafts_never_send_email(self):
        self.case.state = Case.State.DRAFT
        self.case.lawyer = None
        self.case.save()
        for action in ('DRAFT_CREATED', 'DRAFT_UPDATED', 'DOCUMENT_REMOVED', 'DOCUMENT_AVAILABLE'):
            with self.subTest(action=action):
                self.deliver_event(action, self.owner, [])

    def test_private_movement_only_reaches_lawyer_even_for_unknown_action(self):
        for action in ('LEGAL_DRAFT', 'INTERNAL_MESSAGE', 'FUTURE_PRIVATE_EVENT'):
            self.deliver_event(action, self.lawyer, [], public=False)
        self.assertFalse(Notification.objects.filter(recipient=self.owner).exists())

    def test_assignment_reaches_new_lawyer_and_client(self):
        self.deliver_event('ASSIGNED', self.owner, [self.owner.email, self.lawyer.email], public=False)

    def test_unreviewed_events_do_not_send_email(self):
        self.deliver_event('FUTURE_PUBLIC_EVENT', self.lawyer, [])
        self.deliver_event('MANDATE_GENERATED', self.lawyer, [])

    def test_rollback_never_sends_event(self):
        with self.assertRaises(RuntimeError), transaction.atomic():
            changed(self.case, self.lawyer, 'DOCUMENT_AVAILABLE')
            raise RuntimeError('rollback')
        self.assertFalse(deliver_case_email())
        self.assertFalse(Notification.objects.exists())

    def test_previously_queued_document_email_is_cancelled(self):
        notice = Notification.objects.create(recipient=self.owner, case=self.case,
            source_key='old-document', kind='DOCUMENT_AVAILABLE', title='Document verified')
        queued = CaseEmail.objects.create(notification=notice, available_at=timezone.now())
        self.assertTrue(deliver_case_email())
        queued.refresh_from_db()
        self.assertIsNotNone(queued.cancelled_at)
        self.assertIsNone(queued.sent_at)
        self.assertEqual(queued.last_error, 'NotCaseMovement')
        self.assertEqual(len(mail.outbox), 0)
