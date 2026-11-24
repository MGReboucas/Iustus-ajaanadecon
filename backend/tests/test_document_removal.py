from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.cases.models import CaseEvent
from apps.documents.models import DocumentVersion
from integrations.storage.private import object_path
from jobs.documents import scan_one, purge_removed_one
from . import test_documents as docs


class DocumentRemovalTests(TestCase):
    browser = docs.DocumentTests.browser
    post = docs.DocumentTests.post
    user = docs.DocumentTests.user
    login = docs.DocumentTests.login
    team_login = docs.DocumentTests.team_login
    initiate = docs.DocumentTests.initiate
    content = docs.DocumentTests.content
    complete = docs.DocumentTests.complete
    upload = docs.DocumentTests.upload
    download = docs.DocumentTests.download

    def setUp(self):
        docs.DocumentTests.setUp(self)
        self.case.state = "RASCUNHO"
        self.case.save()

    def remove(self, item, browser=None, csrf=True):
        return self.post(browser or self.customer,
            f"documents/{item.document_id}/versions/{item.pk}/remove", {}, csrf=csrf)

    def test_removes_uploaded_file_and_prevents_completion_download_and_listing(self):
        item = self.upload()
        self.assertTrue(object_path(item.object_key).exists())
        self.assertEqual(self.remove(item).status_code, 204)
        self.assertFalse(object_path(item.object_key).exists())
        item.refresh_from_db()
        self.assertEqual(item.status, "REMOVED")
        self.assertEqual(self.download(item).status_code, 409)
        self.assertEqual(self.complete(item.pk).status_code, 409)
        self.assertEqual(self.content(item.pk).status_code, 409)
        self.assertEqual(self.customer.get(f"/api/v1/cases/{self.case.pk}/documents").json()["results"], [])
        self.assertFalse(scan_one())
        self.assertEqual(self.remove(item).status_code, 204)
        self.assertEqual(CaseEvent.objects.filter(action="DOCUMENT_REMOVED").count(), 1)

    def test_incomplete_and_available_files_can_be_removed_from_draft(self):
        item = DocumentVersion.objects.get(pk=self.initiate().json()["uploadId"])
        self.assertEqual(self.remove(item).status_code, 204)
        available = self.upload()
        with patch("jobs.documents.scan", return_value=True):
            scan_one()
        self.assertEqual(self.remove(available).status_code, 204)

    def test_other_users_csrf_and_submitted_case_cannot_remove(self):
        item = self.upload()
        for browser in (self.stranger, self.admin, self.lawyer):
            self.assertEqual(self.remove(item, browser).status_code, 404)
        self.assertEqual(self.remove(item, csrf=False).status_code, 403)
        for state in ("SUBMETIDO", "EM_TRIAGEM", "ENCERRADO"):
            self.case.state = state
            self.case.save()
            self.assertEqual(self.remove(item).status_code, 409)
        item.refresh_from_db()
        self.assertEqual(item.status, "QUARANTINED")

    def test_removal_revokes_inflight_scanner_lease(self):
        item = self.upload()
        def finish_after_removal(source):
            self.assertEqual(self.remove(item).status_code, 204)
            return True
        with patch("jobs.documents.scan", side_effect=finish_after_removal):
            scan_one()
        item.refresh_from_db()
        self.assertEqual(item.status, "REMOVED")
        self.assertFalse(CaseEvent.objects.filter(action="DOCUMENT_AVAILABLE").exists())

    def test_failed_deletion_and_late_upload_are_cleaned_after_urls_expire(self):
        item = self.upload()
        with patch("integrations.storage.private.delete_object", side_effect=ConnectionError):
            self.assertEqual(self.remove(item).status_code, 204)
        self.assertFalse(purge_removed_one(case_id=self.case.pk))
        # A previously signed upload can arrive late, but cannot be confirmed.
        object_path(item.object_key).write_bytes(docs.PDF)
        self.assertEqual(self.complete(item.pk).status_code, 409)
        DocumentVersion.objects.filter(pk=item.pk).update(available_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(purge_removed_one(case_id=self.case.pk))
        self.assertFalse(object_path(item.object_key).exists())
        self.assertFalse(purge_removed_one(case_id=self.case.pk))
        item.refresh_from_db()
        self.assertEqual(item.last_error, "")
