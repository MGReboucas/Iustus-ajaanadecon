import base64
import hashlib
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from moto import mock_aws
from botocore.exceptions import ClientError

from apps.documents.models import DocumentVersion
from integrations.storage.private import s3_client, remote_key
from jobs.documents import scan_one
from . import test_documents as documents

PDF = documents.PDF


@override_settings(DOCUMENT_STORAGE_BACKEND="s3", DOCUMENT_DIRECT_UPLOAD_ENABLED=True,
                   DOCUMENT_S3_BUCKET="synthetic-private", DOCUMENT_S3_ENDPOINT="",
                   DOCUMENT_S3_ACCESS_KEY="testing", DOCUMENT_S3_SECRET_KEY="testing")
class DirectUploadTests(TestCase):
    browser = documents.DocumentTests.browser
    post = documents.DocumentTests.post
    user = documents.DocumentTests.user
    login = documents.DocumentTests.login
    team_login = documents.DocumentTests.team_login
    initiate = documents.DocumentTests.initiate
    complete = documents.DocumentTests.complete
    download = documents.DocumentTests.download

    def setUp(self):
        aws = mock_aws()
        aws.start()
        self.addCleanup(aws.stop)
        documents.DocumentTests.setUp(self)
        s3_client().create_bucket(Bucket="synthetic-private")

    def authorize(self, pk, body=PDF, browser=None, csrf=True):
        return self.post(browser or self.customer, f"uploads/{pk}/authorize",
                         {"checksum": hashlib.sha256(body).hexdigest()}, csrf=csrf)

    def put_object(self, item, body):
        # Simula o objeto recebido pelo S3. Moto não comprova CORS/assinatura AWS.
        return s3_client().put_object(Bucket="synthetic-private", Key=remote_key(item.object_key),
            Body=body, ContentType="application/octet-stream", IfNoneMatch="*",
            ChecksumSHA256=base64.b64encode(hashlib.sha256(body).digest()).decode(),
            ServerSideEncryption="AES256")

    def test_large_direct_upload_keeps_quarantine_integrity_and_private_download(self):
        body = PDF + b" " * (5 * 1024 * 1024)
        started = self.initiate(content=body)
        self.assertEqual(started.status_code, 201)
        self.assertTrue(started.json()["directUpload"])
        item = DocumentVersion.objects.get(pk=started.json()["uploadId"])
        authorized = self.authorize(item.pk, body)
        self.assertEqual(authorized.status_code, 200)
        data = authorized.json()
        query = parse_qs(urlsplit(data["url"]).query)
        self.assertEqual(urlsplit(data["url"]).scheme, "https")
        self.assertEqual(query["X-Amz-Expires"], ["300"])
        signed = set(query["X-Amz-SignedHeaders"][0].split(";"))
        self.assertTrue({"content-length", "content-type", "if-none-match",
                         "x-amz-checksum-sha256", "x-amz-server-side-encryption"} <= signed)
        self.assertEqual(data["headers"]["If-None-Match"], "*")
        self.assertNotIn("Content-Length", data["headers"])
        self.assertIn("no-store", authorized["Cache-Control"])
        self.put_object(item, body)
        self.assertEqual(self.complete(item.pk, body).status_code, 202)
        item.refresh_from_db()
        self.assertEqual(item.status, "QUARANTINED")
        self.assertIsNotNone(item.uploaded_at)
        self.assertEqual(self.download(item).status_code, 409)
        self.assertEqual(self.authorize(item.pk, body).status_code, 409)
        with patch("jobs.documents.scan", return_value=True):
            self.assertTrue(scan_one())
        item.refresh_from_db()
        self.assertEqual(item.status, "AVAILABLE")
        link = self.download(item).json()["url"]
        response = self.customer.get(link)
        self.assertEqual(b"".join(response.streaming_content), body)
        self.assertEqual(self.stranger.get(link).status_code, 403)
        with self.assertRaises(ClientError):
            self.put_object(item, body)
        self.assertEqual(self.complete(item.pk, body).status_code, 202)

    def test_authorization_requires_owner_csrf_and_unexpired_upload(self):
        pk = self.initiate().json()["uploadId"]
        self.assertEqual(self.authorize(pk, browser=self.stranger).status_code, 404)
        self.assertEqual(self.authorize(pk, browser=self.lawyer).status_code, 404)
        self.assertEqual(self.authorize(pk, csrf=False).status_code, 403)
        DocumentVersion.objects.filter(pk=pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.authorize(pk).status_code, 409)

    def test_missing_object_can_be_retried_but_tampered_object_is_rejected(self):
        pk = self.initiate().json()["uploadId"]
        self.assertEqual(self.complete(pk).status_code, 409)
        item = DocumentVersion.objects.get(pk=pk)
        self.assertEqual(item.status, "UPLOADING")
        self.put_object(item, PDF + b"extra")
        self.assertEqual(self.complete(pk).status_code, 422)
        item.refresh_from_db()
        self.assertEqual(item.status, "REJECTED")
        self.assertEqual(self.download(item).status_code, 409)

    def test_checksum_and_detected_format_are_verified_before_quarantine(self):
        for body in (b"X" * len(PDF), PDF[:-1] + b"X"):
            pk = self.initiate().json()["uploadId"]
            item = DocumentVersion.objects.get(pk=pk)
            self.put_object(item, body)
            self.assertEqual(self.complete(pk).status_code, 422)
            item.refresh_from_db()
            self.assertEqual(item.status, "REJECTED")

    def test_revocation_blocks_completion_even_if_object_was_uploaded(self):
        pk = self.initiate().json()["uploadId"]
        item = DocumentVersion.objects.get(pk=pk)
        self.put_object(item, PDF)
        self.owner.is_active = False
        self.owner.save()
        self.assertEqual(self.complete(pk).status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.status, "UPLOADING")

    @override_settings(DOCUMENT_DIRECT_UPLOAD_ENABLED=False)
    def test_direct_upload_is_opt_in(self):
        started = self.initiate()
        self.assertFalse(started.json()["directUpload"])
        self.assertEqual(self.authorize(started.json()["uploadId"]).status_code, 503)
