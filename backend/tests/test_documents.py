import hashlib
import socket
import struct
import tempfile
from datetime import timedelta
from io import BytesIO
from threading import Thread
from unittest.mock import patch
from urllib.parse import urlsplit

from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone

from apps.cases.models import Case, CaseEvent, InformationRequest
from apps.documents.models import Document, DocumentVersion, RequestAttachment
from integrations.scanner.clamav import scan
from integrations.storage.private import object_path
from jobs.documents import scan_one
from . import test_identity as identity

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


class DocumentTests(TestCase):
    browser = identity.IdentityTests.browser
    post = identity.IdentityTests.post
    user = identity.IdentityTests.user
    login = identity.IdentityTests.login
    team_login = identity.IdentityTests.team_login

    def test_upload_and_list_share_document_version_contract(self):
        result = self.post(self.customer, f"cases/{self.case.pk}/documents/uploads", {
            "filename": "contract.pdf", "sizeBytes": len(PDF), "mime": "application/pdf"})
        self.assertEqual(result.status_code, 201, result.content)
        upload = result.json()
        self.assertEqual(set(upload), {"uploadId", "uploadUrl", "expiresAt", "directUpload", "version"})
        version = upload["version"]
        self.assertEqual(set(version), {"id", "documentId", "number", "uploadedById", "filename",
            "sizeBytes", "status", "statusLabel", "createdAt"})
        self.assertEqual(version["status"], "UPLOADING")
        self.assertIsInstance(version["sizeBytes"], int)
        self.assertIsInstance(upload["directUpload"], bool)
        listing = self.customer.get(f"/api/v1/cases/{self.case.pk}/documents").json()
        self.assertEqual(listing["results"][0], version)

    @override_settings(DOCUMENT_LOCAL_STORAGE_ENABLED=False, DOCUMENT_STORAGE_ROOT=None)
    def test_unconfigured_storage_rejects_before_creating_metadata(self):
        response = self.post(self.customer, f"cases/{self.case.pk}/documents/uploads", {
            "filename": "teste.pdf", "sizeBytes": len(PDF), "mime": "application/pdf"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "DOCUMENT_STORAGE_UNAVAILABLE")
        self.assertEqual(Document.objects.count(), 0)

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config = override_settings(DOCUMENT_LOCAL_STORAGE_ENABLED=True, DOCUMENT_STORAGE_ROOT=folder.name)
        config.enable()
        self.addCleanup(config.disable)
        self.owner = self.user()
        self.customer = self.browser()
        self.login(self.customer, self.owner)
        self.stranger_user = self.user(email="stranger@example.test")
        self.stranger = self.browser()
        self.login(self.stranger, self.stranger_user)
        self.lawyer, self.lawyer_user, *_ = self.team_login("LAWYER", "lawyer@example.test")
        self.admin, self.admin_user, *_ = self.team_login()
        self.case = Case.objects.create(owner=self.owner, lawyer=self.lawyer_user, state="EM_TRIAGEM")

    def initiate(self, browser=None, case=None, content=PDF, **extra):
        return self.post(browser or self.customer, f"cases/{(case or self.case).pk}/documents/uploads",
                         {"filename": "exemplo.pdf", "sizeBytes": len(content), "mime": "application/pdf", **extra})

    def content(self, pk, content=PDF, browser=None, csrf=True):
        browser = browser or self.customer
        headers = {"HTTP_X_CSRFTOKEN": browser.get("/api/v1/auth/csrf").json()["csrfToken"]} if csrf else {}
        return browser.post(f"/api/v1/uploads/{pk}/content", content, content_type="application/octet-stream", **headers)

    def complete(self, pk, content=PDF, browser=None):
        return self.post(browser or self.customer, f"uploads/{pk}/complete", {"checksum": hashlib.sha256(content).hexdigest()})

    def upload(self):
        response = self.initiate()
        self.assertEqual(response.status_code, 201, response.content)
        pk = response.json()["uploadId"]
        self.assertEqual(self.content(pk).status_code, 204)
        self.assertEqual(self.complete(pk).status_code, 202)
        return DocumentVersion.objects.get(pk=pk)

    def download(self, version, browser=None):
        return (browser or self.customer).get(f"/api/v1/documents/{version.document_id}/versions/{version.pk}/download")

    def test_upload_quarantine_scan_and_private_download(self):
        item = self.upload()
        self.assertEqual(item.status, "QUARANTINED")
        self.assertEqual(self.download(item).status_code, 409)
        events = CaseEvent.objects.count()
        self.assertEqual(self.complete(item.pk).status_code, 202)
        self.assertEqual(CaseEvent.objects.count(), events)
        with patch("jobs.documents.scan", return_value=True):
            self.assertTrue(scan_one())
            self.assertFalse(scan_one())
        item.refresh_from_db()
        self.assertEqual(item.status, "AVAILABLE")
        result = self.download(item)
        self.assertEqual(result.status_code, 200)
        response = self.customer.get(result.json()["url"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", response["Cache-Control"])

    def test_other_customer_admin_anonymous_and_transfer_cannot_access(self):
        item = self.upload()
        with patch("jobs.documents.scan", return_value=True):
            scan_one()
        link = self.download(item, self.lawyer).json()["url"]
        for browser in (self.stranger, self.admin):
            self.assertEqual(self.initiate(browser).status_code, 404)
            self.assertEqual(browser.get(f"/api/v1/cases/{self.case.pk}/documents").status_code, 404)
            self.assertEqual(self.download(item, browser).status_code, 404)
            self.assertEqual(self.content(item.pk, browser=browser).status_code, 404)
            self.assertEqual(self.complete(item.pk, browser=browser).status_code, 404)
        self.assertEqual(self.download(item, self.browser()).status_code, 403)
        self.case.lawyer = None
        self.case.save()
        self.assertEqual(self.lawyer.get(link).status_code, 404)
        self.assertEqual(self.download(item, self.lawyer).status_code, 404)

    def test_upload_requires_author_csrf_and_open_case(self):
        pk = self.initiate().json()["uploadId"]
        self.assertEqual(self.content(pk, csrf=False).status_code, 403)
        self.assertEqual(self.content(pk, browser=self.lawyer).status_code, 404)
        self.assertEqual(self.complete(pk).status_code, 409)
        self.case.state = "RECUSADO"
        self.case.save()
        self.assertEqual(self.content(pk).status_code, 409)
        self.assertEqual(self.initiate().status_code, 409)

    def test_oversize_extension_mime_and_checksum_validation(self):
        self.assertEqual(self.initiate(sizeBytes=20 * 1024 * 1024 + 1).status_code, 400)
        self.assertEqual(self.initiate(filename="document.exe").status_code, 422)
        self.assertEqual(self.initiate(mime="text/html").status_code, 400)
        pk = self.initiate().json()["uploadId"]
        self.assertEqual(self.content(pk, PDF + b"extra").status_code, 422)
        self.assertEqual(self.content(pk, PDF[:-1]).status_code, 422)
        self.assertEqual(self.content(pk).status_code, 204)
        self.assertEqual(self.content(pk).status_code, 409)
        self.assertEqual(self.complete(pk, b"bad checksum").status_code, 422)
        item = DocumentVersion.objects.get(pk=pk)
        self.assertEqual(item.status, "REJECTED")
        self.assertEqual(self.download(item).status_code, 409)
        fake = b"<html>not a pdf</html>"
        pk = self.initiate(content=fake).json()["uploadId"]
        self.assertEqual(self.content(pk, fake).status_code, 204)
        self.assertEqual(self.complete(pk, fake).status_code, 422)

    def test_expired_upload_and_unknown_fields_denied(self):
        self.assertEqual(self.initiate(object_key="override").status_code, 400)
        pk = self.initiate().json()["uploadId"]
        DocumentVersion.objects.filter(pk=pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.content(pk).status_code, 409)

    def test_versions_are_immutable_and_stale_version_is_rejected(self):
        first = self.upload()
        data = {"filename": "nova.pdf", "sizeBytes": len(PDF), "mime": "application/pdf", "previousVersion": 1}
        route = f"documents/{first.document_id}/versions"
        result = self.post(self.customer, route, data)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["version"]["number"], 2)
        self.assertEqual(self.post(self.customer, route, data).status_code, 409)
        self.assertEqual(self.post(self.stranger, route, {**data, "previousVersion": 2}).status_code, 404)
        self.assertEqual(object_path(first.object_key).read_bytes(), PDF)
        listed = self.customer.get(f"/api/v1/cases/{self.case.pk}/documents").json()
        self.assertEqual(len(listed["results"]), 2)
        self.assertNotIn("object_key", str(listed))

    def test_scanner_failure_retries_virus_rejects_and_integrity_is_rechecked(self):
        item = self.upload()
        with patch("jobs.documents.scan", side_effect=ConnectionError):
            scan_one()
        item.refresh_from_db()
        self.assertEqual(item.status, "ERROR")
        self.assertEqual(item.attempts, 1)
        self.assertEqual(self.download(item).status_code, 409)
        self.assertFalse(scan_one())
        DocumentVersion.objects.filter(pk=item.pk).update(available_at=timezone.now())
        with patch("jobs.documents.scan", return_value=False):
            scan_one()
        item.refresh_from_db()
        self.assertEqual(item.status, "REJECTED")
        self.assertFalse(scan_one())
        tampered = self.upload()
        object_path(tampered.object_key).write_bytes(PDF + b"changed")
        with patch("jobs.documents.scan") as scanner:
            scan_one()
            scanner.assert_not_called()
        tampered.refresh_from_db()
        self.assertEqual(tampered.status, "REJECTED")

    def test_worker_recovers_expired_lease_and_does_not_publish_stale_result(self):
        import uuid
        item = self.upload()
        DocumentVersion.objects.filter(pk=item.pk).update(status="SCANNING", lease_id=uuid.uuid4(),
            lease_until=timezone.now() - timedelta(seconds=1), attempts=1)
        with patch("jobs.documents.scan", return_value=True):
            scan_one()
        item.refresh_from_db()
        self.assertEqual(item.status, "AVAILABLE")
        self.assertEqual(item.attempts, 2)
        another = self.upload()

        def replaced_lease(source):
            DocumentVersion.objects.filter(pk=another.pk).update(lease_id=uuid.uuid4())
            return True

        with patch("jobs.documents.scan", side_effect=replaced_lease):
            scan_one()
        another.refresh_from_db()
        self.assertEqual(another.status, "SCANNING")
        self.assertEqual(self.download(another).status_code, 409)
        DocumentVersion.objects.filter(pk=another.pk).update(lease_until=timezone.now() - timedelta(seconds=1), attempts=5)
        self.assertTrue(scan_one())
        self.assertFalse(scan_one())
        another.refresh_from_db()
        self.assertEqual(another.status, "ERROR")

    def test_download_token_expires_and_is_bound_to_session_and_version(self):
        item = self.upload()
        with patch("jobs.documents.scan", return_value=True):
            scan_one()
        url = self.download(item).json()["url"]
        self.assertEqual(self.stranger.get(url).status_code, 403)
        with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() + 301):
            self.assertEqual(self.customer.get(url).status_code, 403)
        self.assertEqual(self.customer.get(urlsplit(url).path + "?token=forged").status_code, 403)
        self.post(self.customer, "auth/logout")
        self.login(self.customer, self.owner)
        self.assertEqual(self.customer.get(url).status_code, 403)

    def test_response_only_links_available_own_versions_from_same_case(self):
        item = self.upload()
        pending = InformationRequest.objects.create(case=self.case, author=self.lawyer_user, description="Envie documento")
        self.case.refresh_from_db()
        self.case.state = "AGUARDANDO_CLIENTE"
        self.case.save()
        route = f"cases/{self.case.pk}/requests/{pending.pk}/response"
        data = {"version": self.case.version, "text": "Segue documento fictício", "documentVersionIds": [str(item.pk)]}
        self.assertEqual(self.post(self.customer, route, data).status_code, 422)
        with patch("jobs.documents.scan", return_value=True):
            scan_one()
        self.case.refresh_from_db()
        data["version"] = self.case.version
        other_case = Case.objects.create(owner=self.owner)
        foreign_document = Document.objects.create(case=other_case, created_by=self.owner)
        foreign = DocumentVersion.objects.create(document=foreign_document, number=1, uploaded_by=self.owner,
            filename="other.pdf", size_bytes=1, declared_mime="application/pdf", object_key="f" * 32,
            expires_at=timezone.now(), status="AVAILABLE")
        self.assertEqual(self.post(self.customer, route, {**data, "documentVersionIds": [str(foreign.pk)]}).status_code, 422)
        self.assertEqual(RequestAttachment.objects.count(), 0)
        self.assertEqual(self.post(self.customer, route, data).status_code, 200)
        self.assertEqual(RequestAttachment.objects.get().version_id, item.pk)
        result = self.lawyer.get(f"/api/v1/cases/{self.case.pk}/requests").json()
        self.assertEqual(result["results"][0]["attachments"][0]["id"], str(item.pk))


class ClamAVProtocolTests(SimpleTestCase):
    def test_stream_framing_clean_infected_and_error(self):
        # Servidor TCP efêmero testa o protocolo real; não simula um antivírus instalado.
        for response, expected in ((b"stream: OK\x00", True), (b"stream: Test FOUND\x00", False),
                                   (b"stream: size limit ERROR\x00", None), (b"stream: OK", None)):
            with self.subTest(response=response), socket.socket() as server:
                server.bind(("127.0.0.1", 0))
                server.listen(1)
                received = []

                def serve():
                    with server.accept()[0] as connection:
                        connection.settimeout(5)

                        def exact(size):
                            result = b""
                            while len(result) < size:
                                chunk = connection.recv(size - len(result))
                                if not chunk:
                                    raise RuntimeError("truncated fixture")
                                result += chunk
                            return result

                        received.append(exact(10))
                        while size := struct.unpack("!I", exact(4))[0]:
                            received.append(exact(size))
                        connection.sendall(response)

                worker = Thread(target=serve, daemon=True)
                worker.start()
                with override_settings(DOCUMENT_SCANNER_PORT=server.getsockname()[1], DOCUMENT_SCANNER_TIMEOUT=3):
                    if expected is None:
                        with self.assertRaises(RuntimeError):
                            scan(BytesIO(PDF))
                    else:
                        self.assertIs(scan(BytesIO(PDF)), expected)
                worker.join(timeout=5)
                self.assertFalse(worker.is_alive())
                self.assertEqual(received, [b"zINSTREAM\x00", PDF])
