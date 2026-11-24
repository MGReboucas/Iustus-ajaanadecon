from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.cases.models import CaseEvent
from apps.documents.models import DocumentVersion
from integrations.storage.private import remote_key, s3_client
from jobs.documents import scan_one
from .test_direct_upload import DirectUploadTests, PDF


@override_settings(DOCUMENT_STORAGE_BACKEND="s3", DOCUMENT_SCANNER_BACKEND="guardduty",
                   DOCUMENT_DIRECT_UPLOAD_ENABLED=True, DOCUMENT_S3_BUCKET="synthetic-private",
                   DOCUMENT_S3_ENDPOINT="", DOCUMENT_S3_ACCESS_KEY="testing", DOCUMENT_S3_SECRET_KEY="testing")
class GuardDutyTests(TestCase):
    # Reuse fixtures, without inheriting the ClamAV-specific test cases.
    browser = DirectUploadTests.browser
    post = DirectUploadTests.post
    user = DirectUploadTests.user
    login = DirectUploadTests.login
    team_login = DirectUploadTests.team_login
    initiate = DirectUploadTests.initiate
    complete = DirectUploadTests.complete
    download = DirectUploadTests.download
    setUp = DirectUploadTests.setUp
    put_object = DirectUploadTests.put_object

    def upload(self):
        result = self.initiate()
        self.assertEqual(result.status_code, 201)
        item = DocumentVersion.objects.get(pk=result.json()["uploadId"])
        self.put_object(item, PDF)
        self.assertEqual(self.complete(item.pk).status_code, 202)
        item.refresh_from_db()
        return item

    def tag(self, item, value):
        s3_client().put_object_tagging(Bucket="synthetic-private", Key=remote_key(item.object_key),
            Tagging={"TagSet": [{"Key": "GuardDutyMalwareScanStatus", "Value": value}]})

    def due(self, item):
        DocumentVersion.objects.filter(pk=item.pk).update(available_at=timezone.now() - timedelta(seconds=1))

    def listing(self, browser=None):
        return (browser or self.customer).get(f"/api/v1/cases/{self.case.pk}/documents")

    def test_pending_then_clean_is_reconciled_without_worker_and_downloads_privately(self):
        item = self.upload()
        self.assertEqual(self.listing().json()["results"][0]["status"], "QUARANTINED")
        self.assertEqual(self.download(item).status_code, 409)
        with patch("jobs.documents.verdict") as reader:
            self.listing()
            reader.assert_not_called()  # persisted cooldown
        self.tag(item, "NO_THREATS_FOUND")
        self.due(item)
        with patch("jobs.documents.scan") as clamav:
            self.assertEqual(self.listing().json()["results"][0]["status"], "AVAILABLE")
            clamav.assert_not_called()
        item.refresh_from_db()
        self.assertIsNotNone(item.scanned_at)
        events = CaseEvent.objects.filter(action="DOCUMENT_AVAILABLE").count()
        self.assertEqual(events, 1)
        self.listing()
        self.assertEqual(CaseEvent.objects.filter(action="DOCUMENT_AVAILABLE").count(), events)
        url = self.download(item).json()["url"]
        response = self.customer.get(url)
        self.assertEqual(b"".join(response.streaming_content), PDF)
        self.assertEqual(self.stranger.get(url).status_code, 403)

    def test_no_nonclean_result_can_release_a_document(self):
        for value, expected in [("THREATS_FOUND", "REJECTED"), ("UNSUPPORTED", "REJECTED"),
                                ("ACCESS_DENIED", "ERROR"), ("FAILED", "ERROR"), ("unknown", "ERROR")]:
            with self.subTest(value=value):
                item = self.upload()
                self.tag(item, value)
                scan_one(case_id=self.case.pk)
                item.refresh_from_db()
                self.assertEqual(item.status, expected)
                self.assertEqual(self.download(item).status_code, 409)

    def test_pending_does_not_exhaust_attempts_before_aws_finishes(self):
        item = self.upload()
        DocumentVersion.objects.filter(pk=item.pk).update(attempts=10)
        self.listing()
        self.tag(item, "NO_THREATS_FOUND")
        self.due(item)
        self.listing()
        item.refresh_from_db()
        self.assertEqual(item.status, "AVAILABLE")

    def test_access_failure_stays_blocked_and_recovers_after_permissions_are_fixed(self):
        item = self.upload()
        with patch("jobs.documents.verdict", side_effect=RuntimeError("private credentials")):
            self.assertEqual(self.listing().status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, "ERROR")
        self.assertEqual(item.last_error, "RuntimeError")
        self.assertEqual(self.download(item).status_code, 409)
        self.tag(item, "NO_THREATS_FOUND")
        self.due(item)
        self.listing()
        item.refresh_from_db()
        self.assertEqual(item.status, "AVAILABLE")

    def test_clean_tag_does_not_bypass_integrity_or_network_errors(self):
        for invalid in (True, False):
            item = self.upload()
            self.tag(item, "NO_THREATS_FOUND")
            failure = ("wrong checksum", "application/pdf") if invalid else None
            with patch("jobs.documents.inspect_file", return_value=failure,
                       side_effect=None if invalid else ConnectionError("private host")):
                self.listing()
            item.refresh_from_db()
            self.assertEqual(item.status, "REJECTED" if invalid else "ERROR")
            self.assertEqual(self.download(item).status_code, 409)

    def test_authorization_happens_before_scanner_access(self):
        self.upload()
        with patch("jobs.documents.verdict") as reader:
            for browser in (self.stranger, self.admin):
                self.assertEqual(self.listing(browser).status_code, 404)
            reader.assert_not_called()

    def test_only_requested_case_and_one_due_file_are_processed(self):
        from apps.cases.models import Case
        first, second = self.upload(), self.upload()
        self.tag(first, "NO_THREATS_FOUND")
        self.tag(second, "NO_THREATS_FOUND")
        another = Case.objects.create(owner=self.owner)
        self.customer.get(f"/api/v1/cases/{another.pk}/documents")
        self.assertEqual(DocumentVersion.objects.filter(status="AVAILABLE").count(), 0)
        self.listing()
        self.assertEqual(DocumentVersion.objects.filter(status="AVAILABLE").count(), 1)
        self.listing()
        self.assertEqual(DocumentVersion.objects.filter(status="AVAILABLE").count(), 2)

    def test_download_rechecks_result_and_fails_closed_on_tag_removal_or_error(self):
        item = self.upload()
        self.tag(item, "NO_THREATS_FOUND")
        self.listing()
        url = self.download(item).json()["url"]
        self.tag(item, "THREATS_FOUND")
        self.assertEqual(self.customer.get(url).status_code, 409)
        s3_client().delete_object_tagging(Bucket="synthetic-private", Key=remote_key(item.object_key))
        self.assertEqual(self.download(item).status_code, 409)
        with patch("integrations.scanner.guardduty.verdict", side_effect=ConnectionError):
            self.assertEqual(self.customer.get(url).status_code, 409)

    def test_expired_lease_recovers_and_stale_result_is_discarded(self):
        import uuid
        item = self.upload()
        self.tag(item, "NO_THREATS_FOUND")
        DocumentVersion.objects.filter(pk=item.pk).update(status="SCANNING", lease_id=uuid.uuid4(),
            lease_until=timezone.now() - timedelta(seconds=1))
        self.listing()
        item.refresh_from_db()
        self.assertEqual(item.status, "AVAILABLE")
        other = self.upload()
        def stolen(key):
            DocumentVersion.objects.filter(pk=other.pk).update(lease_id=uuid.uuid4())
            return "REJECTED", "MALWARE_DETECTED"
        with patch("jobs.documents.verdict", side_effect=stolen):
            self.listing()
        other.refresh_from_db()
        self.assertEqual(other.status, "SCANNING")
