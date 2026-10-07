from datetime import timedelta
from django.http import Http404
from django.test import TestCase
from django.utils import timezone
from apps.cases.models import Case, CaseEvent
from apps.identity.models import User
from apps.identity.security import IdentityError
from apps.legal.models import ServiceProposal
from apps.legal.proposals import publish_proposal, decide_proposal, proposal_list


class ProposalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.test", None)
        self.other = User.objects.create_user("other@example.test", None)
        self.lawyer = User.objects.create_user("lawyer@example.test", None, role="LAWYER")
        self.case = Case.objects.create(owner=self.owner, lawyer=self.lawyer, state=Case.State.TRIAGE)

    def publish(self, **overrides):
        self.case.refresh_from_db()
        data = dict(scope="Prepare the agreed defense", fee_cents=120000, expenses="Court fees excluded",
                    payment_terms="Terms individually agreed", valid_until=timezone.now()+timedelta(days=7))
        data.update(overrides)
        return publish_proposal(self.lawyer, self.case.pk, self.case.version, **data)

    def decide(self, proposal, accepted=True):
        self.case.refresh_from_db()
        return decide_proposal(self.owner, self.case.pk, proposal.pk, self.case.version, accepted=accepted)

    def test_acceptance_is_audited_idempotent_and_does_not_start_work(self):
        p = self.publish()
        self.case.refresh_from_db()
        version = self.case.version
        self.decide(p)
        decide_proposal(self.owner, self.case.pk, p.pk, version, accepted=True)
        p.refresh_from_db(); self.case.refresh_from_db()
        self.assertEqual(p.status, "ACCEPTED")
        self.assertEqual(p.decided_by, self.owner)
        self.assertIsNotNone(p.decided_at)
        self.assertEqual(self.case.state, Case.State.TRIAGE)
        self.assertEqual(CaseEvent.objects.filter(action="PROPOSAL_ACCEPTED").count(), 1)
        self.assertEqual(proposal_list(self.owner, self.case.pk).count(), 1)

    def test_new_version_supersedes_open_but_preserves_accepted_terms(self):
        old = self.publish()
        current = self.publish(fee_cents=150000)
        old.refresh_from_db()
        self.assertEqual(old.status, "SUPERSEDED")
        with self.assertRaises(IdentityError): self.decide(old)
        self.decide(current)
        newer = self.publish(fee_cents=180000)
        current.refresh_from_db()
        self.assertEqual((current.status, current.fee_cents), ("ACCEPTED", 150000))
        self.assertEqual(newer.number, 3)
        self.assertEqual(ServiceProposal.objects.filter(status="OPEN").count(), 1)

    def test_expired_closed_and_conflicting_decisions_are_rejected(self):
        p = self.publish()
        ServiceProposal.objects.filter(pk=p.pk).update(valid_until=timezone.now()-timedelta(seconds=1))
        with self.assertRaises(IdentityError): self.decide(p)
        p = self.publish()
        self.decide(p, False)
        with self.assertRaises(IdentityError): self.decide(p, True)
        self.case.state = Case.State.CLOSED; self.case.save()
        with self.assertRaises(IdentityError): self.publish()

    def test_cross_client_and_unassigned_lawyer_cannot_access(self):
        p = self.publish()
        with self.assertRaises(Http404): proposal_list(self.other, self.case.pk)
        with self.assertRaises(Http404):
            decide_proposal(self.other, self.case.pk, p.pk, 2, accepted=True)
        with self.assertRaises(IdentityError):
            decide_proposal(self.lawyer, self.case.pk, p.pk, 2, accepted=True)
        self.case.lawyer = None; self.case.save()
        with self.assertRaises(Http404): proposal_list(self.lawyer, self.case.pk)

    def test_invalid_terms_and_stale_case_do_not_replace_proposal(self):
        p = self.publish()
        for changes in ({"fee_cents": -1}, {"fee_cents": True}, {"scope": " "},
                        {"valid_until": timezone.now()-timedelta(days=1)}):
            with self.subTest(changes=changes), self.assertRaises(IdentityError): self.publish(**changes)
        with self.assertRaises(IdentityError):
            decide_proposal(self.owner, self.case.pk, p.pk, 1, accepted=True)
        p.refresh_from_db()
        self.assertEqual(p.status, "OPEN")
        self.assertEqual(ServiceProposal.objects.count(), 1)
