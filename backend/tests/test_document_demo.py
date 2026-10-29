"""CI coverage for the isolated, unscanned demonstration workflow."""
from io import BytesIO
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, override_settings
from apps.documents.models import DocumentVersion
from apps.identity.security import IdentityError
from integrations.storage import supabase
from integrations.storage.private import write_stream
from . import test_documents as documents

PDF = documents.PDF


class DemoTests(TestCase):
    browser = documents.DocumentTests.browser
    post = documents.DocumentTests.post
    user = documents.DocumentTests.user
    login = documents.DocumentTests.login
    team_login = documents.DocumentTests.team_login
    initiate = documents.DocumentTests.initiate
    content = documents.DocumentTests.content
    complete = documents.DocumentTests.complete
    upload = documents.DocumentTests.upload
    download = documents.DocumentTests.download

    def setUp(self):
        documents.DocumentTests.setUp(self)
        config = override_settings(DOCUMENT_DEMO_ENABLED=True, DOCUMENT_DEMO_EMAILS=[self.owner.email.lower()])
        config.enable()
        self.addCleanup(config.disable)

    def test_demo_download_never_claims_scanning_and_disable_revokes_link(self):
        item = self.upload()
        self.assertEqual(item.status, "DEMO_UNVERIFIED")
        self.assertIsNone(item.scanned_at)
        url = self.download(item).json()["url"]
        response = self.customer.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF)
        self.assertEqual(self.download(item, self.stranger).status_code, 404)
        self.assertEqual(self.download(item, self.lawyer).status_code, 403)
        with override_settings(DOCUMENT_DEMO_ENABLED=False):
            self.assertEqual(self.customer.get(url).status_code, 403)
        with override_settings(DOCUMENT_DEMO_EMAILS=[]):
            self.assertEqual(self.customer.get(url).status_code, 403)

    def test_non_allowlisted_uploader_and_large_files_are_rejected(self):
        self.assertEqual(self.initiate(browser=self.lawyer).status_code, 403)
        self.assertEqual(self.initiate(sizeBytes=3 * 1024 * 1024 + 1).status_code, 422)
        self.assertEqual(DocumentVersion.objects.count(), 0)

    def test_checksum_validation_remains_required(self):
        pk = self.initiate().json()["uploadId"]
        self.assertEqual(self.content(pk).status_code, 204)
        self.assertEqual(self.complete(pk, content=PDF + b"changed").status_code, 422)
        self.assertEqual(DocumentVersion.objects.get(pk=pk).status, "REJECTED")


@override_settings(DOCUMENT_STORAGE_BACKEND="supabase", DOCUMENT_DEMO_ENABLED=True,
                   DOCUMENT_SUPABASE_URL="https://synthetic.supabase.co",
                   DOCUMENT_SUPABASE_BUCKET="demo-private", DOCUMENT_SUPABASE_SERVICE_KEY="synthetic")
class SupabaseTests(SimpleTestCase):
    def test_public_bucket_blocks_write(self):
        with patch.object(supabase, "request", return_value=BytesIO(b'{"public":true}')) as request:
            with self.assertRaises(IdentityError):
                supabase.write("a" * 32, BytesIO(PDF), len(PDF))
            self.assertEqual(request.call_count, 1)

    def test_upload_uses_private_demo_path_and_exact_bytes(self):
        with patch.object(supabase, "request", side_effect=[BytesIO(b'{"public":false}'), BytesIO(b'{}')]) as request:
            write_stream("a" * 32, BytesIO(PDF), len(PDF), demo_upload=True)
            self.assertEqual(request.call_args.args, ("object/demo-private/demo/" + "a" * 32, "POST", PDF))

    def test_generated_documents_cannot_use_demo_storage(self):
        with self.assertRaises(IdentityError):
            write_stream("a" * 32, BytesIO(PDF), len(PDF))
