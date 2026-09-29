from datetime import timedelta
from io import BytesIO
from unittest.mock import patch
from django.core import mail
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from moto import mock_aws
from apps.cases.models import Case
from apps.legal.models import LegalTask
from apps.communication.models import CaseEmail, Notification
from apps.communication.services import create_notice
from jobs.communication import deliver_case_email, schedule_reminders
from integrations.storage.private import write_stream, open_object, delete_object, inspect_file, InvalidFile, s3_client, remote_key
from .test_identity import IdentityTests

class OperationsTests(TestCase):
    browser = IdentityTests.browser
    post = IdentityTests.post
    user = IdentityTests.user
    login = IdentityTests.login
    team_login = IdentityTests.team_login
    def setUp(self):
        self.owner = self.user()
        self.client = self.browser()
        self.login(self.client, self.owner)
        self.admin, self.admin_user, *_ = self.team_login()
        self.lawyer, self.lawyer_user, *_ = self.team_login("LAWYER", "lawyer@example.test")
        self.case = Case.objects.create(owner=self.owner, lawyer=self.lawyer_user, state=Case.State.TRACKING, title="Segredo")
    def notice(self, recipient=None, key="event:synthetic"):
        return create_notice(recipient_id=(recipient or self.owner).pk, source_key=key, case=self.case, kind="TEST", title="Segredo no título")
    def test_delivery_is_generic_deduplicated_and_honors_opt_out(self):
        self.notice(); self.notice()
        self.assertEqual(CaseEmail.objects.count(), 1)
        self.assertTrue(deliver_case_email()); self.assertFalse(deliver_case_email())
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Segredo", mail.outbox[0].body + mail.outbox[0].subject)
        self.notice(key="next")
        self.owner.case_email_enabled = False; self.owner.save()
        self.assertTrue(deliver_case_email()); self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(CaseEmail.objects.filter(cancelled_at__isnull=False).count(), 1)
    def test_reassignment_cancels_queued_email(self):
        self.notice(self.lawyer_user)
        self.case.lawyer = None; self.case.save()
        deliver_case_email()
        self.assertTrue(CaseEmail.objects.get().cancelled_at)
        self.assertEqual(len(mail.outbox), 0)
    def test_reminders_cancel_exact_rescheduled_task_and_hide_internal_deadlines(self):
        task = LegalTask.objects.create(case=self.case, kind="DEADLINE", title="Interno", due_at=timezone.now()+timedelta(hours=1))
        schedule_reminders(); schedule_reminders()
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.get().recipient_id, self.lawyer_user.pk)
        task.due_at += timedelta(days=2); task.save()
        LegalTask.objects.create(case=self.case, kind="HEARING", title="Outro compromisso", due_at=timezone.now())
        deliver_case_email()
        self.assertTrue(CaseEmail.objects.get().cancelled_at)
        schedule_reminders()
        self.assertEqual(Notification.objects.count(), 3)
    def test_mail_failure_schedules_retry_without_sensitive_error(self):
        self.notice()
        with patch("jobs.communication.EmailMessage.send", side_effect=RuntimeError("secret")):
            deliver_case_email()
        item = CaseEmail.objects.get()
        self.assertEqual(item.last_error, "RuntimeError")
        self.assertIsNone(item.sent_at)
        self.assertFalse(deliver_case_email())
        item.available_at = timezone.now(); item.save()
        self.assertTrue(deliver_case_email())
        self.assertEqual(len(mail.outbox), 1)
    def test_profile_strict_fields_and_csrf(self):
        data = {"name": "Nome atualizado", "caseEmailEnabled": False}
        self.assertEqual(self.client.patch("/api/v1/me", data, content_type="application/json").status_code, 403)
        token = self.client.get("/api/v1/auth/csrf").json()["csrfToken"]
        result = self.client.patch("/api/v1/me", data, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertFalse(result.json()["user"]["caseEmailEnabled"])
        result = self.client.patch("/api/v1/me", {**data, "role": "ADMIN"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 400)
    def test_admin_access_revokes_sessions_and_protects_admin_and_assigned_lawyer(self):
        path = f"admin/users/{self.owner.pk}/access"
        data = {"active": False, "version": 1, "reason": "Solicitação sintética do titular"}
        self.assertEqual(self.post(self.client, path, data).status_code, 403)
        self.assertEqual(self.post(self.admin, path, data).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 403)
        self.assertEqual(self.post(self.admin, path, data).status_code, 409)
        self.assertEqual(self.post(self.admin, f"admin/users/{self.admin_user.pk}/access", data).status_code, 403)
        self.assertEqual(self.post(self.admin, f"admin/users/{self.lawyer_user.pk}/access", data).status_code, 409)
        data.update(active=True, version=2)
        self.assertEqual(self.post(self.admin, path, data).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 403)
    def test_privacy_isolation_and_answer_once_without_deleting_data(self):
        result = self.post(self.client, "privacy/requests", {"kind": "DELETION", "description": "Solicito análise de exclusão dos dados."})
        self.assertEqual(result.status_code, 201, result.content)
        pk = result.json()["id"]
        self.assertEqual(self.lawyer.get("/api/v1/privacy/requests").json()["results"], [])
        self.assertEqual(len(self.admin.get("/api/v1/privacy/requests").json()["results"]), 1)
        path = f"privacy/requests/{pk}/resolve"
        data = {"response": "Pedido analisado. Resposta sintética registrada."}
        self.assertEqual(self.post(self.lawyer, path, data).status_code, 403)
        self.assertEqual(self.post(self.admin, path, data).status_code, 200)
        self.assertEqual(self.post(self.admin, path, data).status_code, 409)
        self.assertEqual(self.client.get("/api/v1/privacy/requests").json()["results"][0]["response"], data["response"])
        self.assertTrue(Case.objects.filter(pk=self.case.pk).exists())

@override_settings(DOCUMENT_STORAGE_BACKEND="s3", DOCUMENT_S3_BUCKET="synthetic-private", DOCUMENT_S3_ENDPOINT="", DOCUMENT_S3_ACCESS_KEY="testing", DOCUMENT_S3_SECRET_KEY="testing")
class S3Tests(SimpleTestCase):
    @mock_aws
    def test_private_immutable_roundtrip_and_invalid_sizes(self):
        client = s3_client(); client.create_bucket(Bucket="synthetic-private")
        key, body = "a"*32, b"%PDF-1.4 synthetic"
        write_stream(key, BytesIO(body), len(body))
        with open_object(key) as stream: self.assertEqual(stream.read(), body)
        self.assertEqual(inspect_file(key, len(body))[1], "application/pdf")
        metadata = client.head_object(Bucket="synthetic-private", Key=remote_key(key))
        self.assertEqual(metadata["ServerSideEncryption"], "AES256")
        self.assertEqual(len(client.get_object_acl(Bucket="synthetic-private", Key=remote_key(key))["Grants"]), 1)
        with self.assertRaises(InvalidFile): write_stream(key, BytesIO(body), len(body))
        with self.assertRaises(InvalidFile): write_stream("b"*32, BytesIO(body), 3)
        with self.assertRaises(ValueError): open_object("../invalid")
        delete_object(key)
        with self.assertRaises(FileNotFoundError): open_object(key)


from . import test_documents as documents
@override_settings(DOCUMENT_STORAGE_BACKEND="s3", DOCUMENT_S3_BUCKET="synthetic-private", DOCUMENT_S3_ENDPOINT="", DOCUMENT_S3_ACCESS_KEY="testing", DOCUMENT_S3_SECRET_KEY="testing")
class S3DocumentFlowTests(TestCase):
    browser = documents.DocumentTests.browser
    post = documents.DocumentTests.post
    user = documents.DocumentTests.user
    login = documents.DocumentTests.login
    team_login = documents.DocumentTests.team_login
    setUp = documents.DocumentTests.setUp
    initiate = documents.DocumentTests.initiate
    content = documents.DocumentTests.content
    complete = documents.DocumentTests.complete
    upload = documents.DocumentTests.upload
    download = documents.DocumentTests.download
    @mock_aws
    def test_quarantine_authorized_download_on_s3(self):
        s3_client().create_bucket(Bucket="synthetic-private")
        documents.DocumentTests.test_upload_quarantine_scan_and_private_download(self)

class MaintenanceTests(SimpleTestCase):
    def test_once_is_bounded_and_runs_maintenance(self):
        from django.core.management import call_command
        with patch("jobs.management.commands.run_operations.schedule_reminders") as schedule, \
             patch("jobs.management.commands.run_operations.deliver_one", return_value=True) as identity, \
             patch("jobs.management.commands.run_operations.deliver_case_email", return_value=True) as cases, \
             patch("jobs.management.commands.run_operations.call_command") as cleanup:
            call_command("run_operations", once=True)
        schedule.assert_called_once()
        self.assertEqual(identity.call_count, 100)
        self.assertEqual(cases.call_count, 100)
        cleanup.assert_called_once_with("purge_case_exports", verbosity=0)
