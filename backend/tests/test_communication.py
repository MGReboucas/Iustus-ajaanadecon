from uuid import uuid4

from django.test import TestCase
from django.db import transaction

from apps.cases.models import Case, CaseEvent, InformationRequest
from apps.communication.models import Message, Notification
from apps.communication.services import notify_event
from . import test_cases as cases


class CommunicationTests(TestCase):
    browser = cases.CaseTests.browser
    post = cases.CaseTests.post
    user = cases.CaseTests.user
    login = cases.CaseTests.login
    team_login = cases.CaseTests.team_login

    def setUp(self):
        self.owner = self.user()
        self.client = self.browser()
        self.login(self.client, self.owner)
        self.other_user = self.user(email="other@example.test")
        self.other = self.browser()
        self.login(self.other, self.other_user)
        self.admin, self.admin_user, *_ = self.team_login()
        self.lawyer, self.lawyer_user, *_ = self.team_login("LAWYER", "lawyer@example.test")
        self.colleague, self.colleague_user, *_ = self.team_login("LAWYER", "colleague@example.test")
        self.case = Case.objects.create(owner=self.owner, lawyer=self.lawyer_user, state=Case.State.TRIAGE, title="Caso privado")
        self.path = f"cases/{self.case.pk}/messages"

    def send(self, browser=None, **overrides):
        return self.post(browser or self.client, self.path, {"text": "Mensagem sintética", "clientMessageId": str(uuid4()), **overrides})

    def overview(self, browser=None):
        return (browser or self.client).get("/api/v1/dashboard/overview").json()

    def notices(self, browser=None):
        return (browser or self.client).get("/api/v1/notifications").json()["results"]

    def test_conversation_is_scoped_and_notes_never_reach_client(self):
        public = self.send(self.lawyer, text="<script>alert('texto')</script>")
        self.assertEqual(public.status_code, 201, public.content)
        note = self.send(self.lawyer, text="Estratégia interna", visibility="INTERNAL")
        self.assertEqual(note.status_code, 201)
        self.assertEqual(len(self.notices()), 1)
        self.assertNotIn("Estratégia", str(self.notices()) + str(self.overview()))
        self.assertEqual(len(self.client.get(f"/api/v1/{self.path}").json()["results"]), 1)
        self.assertEqual(len(self.lawyer.get(f"/api/v1/{self.path}").json()["results"]), 2)
        self.assertEqual(self.send(visibility="INTERNAL").status_code, 403)
        for browser in (self.other, self.colleague, self.admin):
            self.assertEqual(browser.get(f"/api/v1/{self.path}").status_code, 404)
            self.assertIn(self.send(browser).status_code, (403, 404))

    def test_retry_returns_same_message_and_notification_and_rejects_changed_payload(self):
        key = str(uuid4())
        first = self.send(clientMessageId=key)
        again = self.send(clientMessageId=key)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(first.json(), again.json())
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(self.send(clientMessageId=key, text="Outro texto").status_code, 409)

    def test_inputs_csrf_and_case_availability(self):
        self.assertEqual(self.browser().get("/api/v1/dashboard/overview").status_code, 403)
        self.assertEqual(self.post(self.client, self.path, {}, csrf=False).status_code, 403)
        for body in ({"text": "   "}, {"text": "x" * 10001}, {"authorId": str(self.owner.pk)}, {"visibility": "OTHER"}, {"clientMessageId": "bad"}):
            self.assertEqual(self.send(**body).status_code, 400)
        for state in (Case.State.DRAFT, Case.State.REJECTED):
            self.case.state = state
            self.case.save()
            self.assertEqual(self.send().status_code, 409)
        self.case.state, self.case.lawyer = Case.State.SUBMITTED, None
        self.case.save()
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(Message.objects.count(), 0)

    def test_read_ownership_idempotence_filters_and_transfer(self):
        self.send()
        notice = self.notices(self.lawyer)[0]
        path = f"notifications/{notice['id']}/read"
        self.assertEqual(self.post(self.client, path, {}).status_code, 404)
        self.assertEqual(self.post(self.colleague, path, {}).status_code, 404)
        first = self.post(self.lawyer, path, {}).json()
        self.assertIsNotNone(first["readAt"])
        self.assertEqual(self.post(self.lawyer, path, {}).json(), first)
        self.assertEqual(self.lawyer.get("/api/v1/notifications?unread=true").json()["results"], [])
        self.assertEqual(self.overview(self.lawyer)["unreadCount"], 0)
        self.send()
        self.case.lawyer = self.colleague_user
        self.case.save()
        self.assertEqual(self.notices(self.lawyer), [])
        self.assertEqual(self.overview(self.lawyer)["totalCases"], 0)
        self.assertEqual(self.post(self.lawyer, path, {}).status_code, 404)
        self.assertEqual(self.lawyer.get(f"/api/v1/{self.path}").status_code, 404)
        self.assertEqual(self.send(self.lawyer).status_code, 404)
        self.assertEqual(len(self.colleague.get(f"/api/v1/{self.path}").json()["results"]), 2)

    def test_overview_counts_full_scope_and_complement_responsibility(self):
        Case.objects.bulk_create([Case(owner=self.owner) for _ in range(24)] + [Case(owner=self.other_user, title="Alheio")])
        self.case.state = Case.State.WAITING
        self.case.save()
        pending = InformationRequest.objects.create(case=self.case, author=self.lawyer_user, description="Informação necessária")
        summary = self.overview()
        self.assertEqual(summary["totalCases"], 25)
        self.assertEqual(summary["attentionCount"], 25)
        self.assertEqual(len(summary["attentionCases"]), 5)
        self.assertEqual(self.overview(self.lawyer)["attentionCount"], 0)
        from django.utils import timezone
        pending.responded_at = timezone.now()
        pending.save()
        self.assertEqual(self.overview()["attentionCount"], 24)
        self.assertEqual(self.overview(self.lawyer)["attentionCount"], 1)
        self.assertEqual(self.overview(self.admin)["totalCases"], 1)
        self.assertNotIn("Caso privado", str(self.overview(self.admin)))
        metadata = self.admin.get(f"/api/v1/cases/{self.case.pk}/summary").json()
        self.assertNotIn("title", metadata)
        self.assertNotIn("description", metadata)
        self.assertEqual(self.client.get(f"/api/v1/cases/{self.case.pk}/summary").status_code, 403)

    def test_event_notices_transaction_deduplication_and_no_private_content(self):
        from apps.cases.services import changed
        with transaction.atomic():
            changed(self.case, self.lawyer_user, "INFORMATION_REQUESTED", "Conteúdo privado do complemento")
        event = CaseEvent.objects.get(case=self.case)
        notify_event(event, self.case)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertNotIn("Conteúdo privado", str(self.notices()))
        try:
            with transaction.atomic():
                changed(self.case, self.lawyer_user, "TRIAGE_STARTED")
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(CaseEvent.objects.count(), 1)

    def test_pagination_excludes_internal_notes_and_foreign_notifications(self):
        Message.objects.bulk_create([Message(case=self.case, author=self.lawyer_user, text=f"Mensagem {i}", visibility="PUBLIC", client_id=uuid4()) for i in range(25)] + [Message(case=self.case, author=self.lawyer_user, text="SEGREDO", visibility="INTERNAL", client_id=uuid4())])
        first = self.client.get(f"/api/v1/{self.path}").json()
        second = self.client.get(f"/api/v1/{self.path}", {"cursor": first["nextCursor"]}).json()
        self.assertEqual(len({row["id"] for row in first["results"] + second["results"]}), 25)
        self.assertNotIn("SEGREDO", str(first) + str(second))
        self.assertIsNone(second["nextCursor"])
        Notification.objects.bulk_create([Notification(case=self.case, recipient=self.owner, source_key=f"test:{i}", kind="MESSAGE", title="Aviso") for i in range(25)])
        first = self.client.get("/api/v1/notifications").json()
        second = self.client.get("/api/v1/notifications", {"cursor": first["nextCursor"]}).json()
        self.assertEqual(len({row["id"] for row in first["results"] + second["results"]}), 25)
        self.assertEqual(self.notices(self.other), [])

    def test_recent_activity_keeps_state_at_time_of_event(self):
        event = CaseEvent.objects.create(case=self.case, actor=self.lawyer_user,
            action="TRIAGE_STARTED", state=Case.State.TRIAGE, version=1)
        Case.objects.filter(pk=self.case.pk).update(state=Case.State.CLOSED, version=2)
        rows = self.overview()["recentActivity"]
        historical = next(row for row in rows if row["id"] == str(event.pk))
        self.assertEqual(historical["stateLabel"], Case.State.TRIAGE.label)
        self.assertNotEqual(historical["stateLabel"], Case.State.CLOSED.label)
        self.assertEqual(self.overview(self.other)["recentActivity"], [])

    def test_case_timeline_and_message_wire_contracts(self):
        detail = self.client.get(f"/api/v1/cases/{self.case.pk}").json()
        self.assertEqual(set(detail), {"id", "reference", "category", "categoryLabel", "state", "stateLabel",
            "version", "lawyerId", "createdAt", "submittedAt", "title", "description", "scopeAcknowledged", "occurredOn"})
        self.assertIsInstance(detail["version"], int)
        self.assertIsNone(detail["submittedAt"])
        self.assertIsNone(detail["occurredOn"])
        self.assertEqual(detail["lawyerId"], str(self.lawyer_user.pk))
        admin_rows = self.admin.get("/api/v1/cases").json()["results"]
        self.assertNotIn("title", admin_rows[0])
        self.assertNotIn("description", admin_rows[0])
        message = self.send().json()
        self.assertEqual(set(message), {"id", "text", "visibility", "authorId", "authorName", "createdAt"})
        self.assertEqual(message["visibility"], "PUBLIC")
        CaseEvent.objects.create(case=self.case, actor=self.lawyer_user, action="TRIAGE_STARTED",
            state=Case.State.TRIAGE, version=1)
        timeline = self.client.get(f"/api/v1/cases/{self.case.pk}/timeline").json()
        self.assertEqual(set(timeline), {"results", "nextCursor"})
        self.assertEqual(set(timeline["results"][0]), {"id", "action", "state", "reason", "createdAt"})
