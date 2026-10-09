import hashlib
import tempfile
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.cases.models import Case, InformationRequest, LocalCaseAccess
from apps.documents.models import RequestAttachment
from apps.legal.models import LegalWork
from apps.communication.models import Notification
from apps.identity.models import ActionToken, User
from apps.identity.security import digest
from jobs.documents import scan_one
from .test_mobile import MobileTests, PASSWORD

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


class MobileFlowTests(TestCase):
    setUp = MobileTests.setUp
    login = MobileTests.login
    headers = MobileTests.headers

    def post(self, path, body, headers):
        return self.client.post('/api/v1/mobile/' + path, body, content_type='application/json', **headers)

    def test_intake_documents_complement_mandate_and_closed_reading(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(
                DOCUMENT_LOCAL_STORAGE_ENABLED=True, DOCUMENT_STORAGE_ROOT=folder,
                CASE_LOCAL_TEST_ACCESS=True, CASE_INTAKE_REQUIRED=True):
            headers = self.headers()
            LocalCaseAccess.objects.create(user=self.user, expires_at=timezone.now()+timedelta(days=1), reason='Liberação sintética')
            response = self.post('cases', {'title': 'Ocorrência sintética', 'description': 'Relato completo para análise do atendimento.',
                'category': 'CONSUMER', 'occurredOn': '2026-01-01', 'scopeAcknowledged': True}, headers)
            self.assertEqual(response.status_code, 201, response.content)
            case_id = response.json()['id']
            base = f'cases/{case_id}'
            submit_headers = {**headers, 'HTTP_IDEMPOTENCY_KEY': 'synthetic-submission-001'}
            self.assertEqual(self.post(base + '/submit', {'version': 1}, submit_headers).status_code, 422)
            upload = self.post(base + '/documents/uploads', {'filename': 'prova.pdf', 'sizeBytes': len(PDF), 'mime': 'application/pdf'}, headers)
            self.assertEqual(upload.status_code, 201, upload.content)
            upload = upload.json()
            self.assertTrue(upload['uploadUrl'].startswith('/api/v1/mobile/'))
            sent = self.client.post(upload['uploadUrl'], PDF, content_type='application/octet-stream', **headers)
            self.assertEqual(sent.status_code, 204, sent.content)
            checksum = {'checksum': hashlib.sha256(PDF).hexdigest()}
            self.assertEqual(self.post(f"uploads/{upload['uploadId']}/complete", checksum, headers).status_code, 202)
            download = f"/api/v1/mobile/documents/{upload['version']['documentId']}/versions/{upload['uploadId']}/content"
            self.assertEqual(self.client.get(download, **headers).status_code, 409)
            with patch('jobs.documents.scan', return_value=True):
                self.assertTrue(scan_one())
            version = Case.objects.get(pk=case_id).version
            first = self.post(base + '/submit', {'version': version}, submit_headers)
            self.assertEqual(first.status_code, 200, first.content)
            self.assertEqual(self.post(base + '/submit', {'version': version}, submit_headers).json(), first.json())
            self.assertEqual(self.client.patch('/api/v1/mobile/' + base, {'version': first.json()['version'], 'title': 'Mudança'}, content_type='application/json', **headers).status_code, 409)
            lawyer = User.objects.create_user('flow-lawyer@example.test', PASSWORD, role='LAWYER')
            case = Case.objects.get(pk=case_id)
            case.lawyer = lawyer; case.state = Case.State.WAITING; case.save()
            pending = InformationRequest.objects.create(case=case, author=lawyer, description='Explique o ocorrido.')
            result = self.post(base + f'/requests/{pending.pk}/response', {'version': case.version, 'text': 'Aqui estão os detalhes adicionais.', 'documentVersionIds': [upload['uploadId']]}, headers)
            self.assertEqual(result.status_code, 200, result.content)
            self.assertTrue(RequestAttachment.objects.filter(request=pending, version_id=upload['uploadId']).exists())
            case.refresh_from_db(); case.state = Case.State.MANDATE; case.save()
            work = LegalWork.objects.create(case=case, scope='Defesa contratada', draft='MINUTA SIGILOSA', published_text='Peça pública revisada')
            workflow = self.client.get('/api/v1/mobile/' + base + '/workflow', **headers).json()
            self.assertNotIn('draft', workflow)
            self.assertEqual(workflow['publishedText'], 'Peça pública revisada')
            for action in ['START', 'VERIFY', 'RETURN_MANDATE', 'DRAFT', 'PUBLISH', 'FILE', 'UPDATE', 'TASK', 'RESCHEDULE', 'COMPLETE', 'CLOSE']:
                self.assertEqual(self.post(base + '/workflow', {'version': case.version, 'action': action}, headers).status_code, 403)
            result = self.post(base + '/workflow', {'version': case.version, 'action': 'SIGN', 'documentId': upload['uploadId']}, headers)
            self.assertEqual(result.status_code, 200, result.content)
            work.refresh_from_db(); self.assertEqual(str(work.signed_mandate_id), upload['uploadId'])
            case.refresh_from_db(); case.state = Case.State.CLOSED; case.save()
            result = self.client.get(download, **headers)
            self.assertEqual(result.status_code, 200); self.assertEqual(b''.join(result.streaming_content), PDF)
            self.assertEqual(self.post(base + '/documents/uploads', {'filename': 'novo.pdf', 'sizeBytes': len(PDF), 'mime': 'application/pdf'}, headers).status_code, 409)

    def test_all_client_resources_enforce_owner_and_bearer(self):
        headers = self.headers()
        other = User.objects.create_user('flow-other@example.test', PASSWORD)
        case = Case.objects.create(owner=other)
        for suffix in ['', '/workflow', '/requests', '/documents', '/timeline', '/messages', '/proposals']:
            path = f'/api/v1/mobile/cases/{case.pk}{suffix}'
            self.assertEqual(self.client.get(path, **headers).status_code, 404, path)
            self.assertEqual(self.client.get(path).status_code, 401, path)
        for path in ['cases/catalog', 'privacy/requests', 'notifications']:
            self.assertEqual(self.client.get('/api/v1/mobile/' + path).status_code, 401)
        self.assertEqual(self.post(f'cases/{case.pk}/documents/uploads', {'filename': 'test.pdf', 'sizeBytes': 10, 'mime': 'application/pdf'}, headers).status_code, 404)

    def test_privacy_profile_notifications_and_read_isolation(self):
        headers = self.headers()
        case = Case.objects.create(owner=self.user)
        other = User.objects.create_user('notice-other@example.test', PASSWORD)
        own = Notification.objects.create(recipient=self.user, case=case, source_key='own', kind='UPDATE', title='Atualização')
        hidden = Notification.objects.create(recipient=other, case=case, source_key='hidden', kind='UPDATE', title='Oculta')
        self.assertEqual(len(self.client.get('/api/v1/mobile/notifications', **headers).json()['results']), 1)
        self.assertEqual(self.post(f'notifications/{own.pk}/read', {}, headers).status_code, 200)
        self.assertEqual(self.post(f'notifications/{hidden.pk}/read', {}, headers).status_code, 404)
        response = self.post('privacy/requests', {'kind': 'DELETION', 'description': 'Solicito exclusão da minha conta.'}, headers)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['status'], 'OPEN')
        changed = self.client.patch('/api/v1/mobile/me', {'name': 'Nome atualizado', 'caseEmailEnabled': False}, content_type='application/json', **headers)
        self.assertEqual(changed.status_code, 200)
        self.user.refresh_from_db(); self.assertFalse(self.user.case_email_enabled)

    def test_registration_confirmation_and_reset_without_cookies(self):
        context = self.client.get('/api/v1/mobile/auth/context').json()
        result = self.post('auth/register', {'name': 'Novo associado', 'email': 'new-mobile@example.test', 'password': PASSWORD, 'policyVersion': context['policyVersion']}, {})
        self.assertEqual(result.status_code, 202, result.content)
        user = User.objects.get(email='new-mobile@example.test')
        raw = 'a' * 43
        ActionToken.objects.create(digest=digest(raw), purpose='VERIFY', user=user, email=user.email, portal='client', auth_version=user.auth_version, expires_at=timezone.now()+timedelta(hours=1))
        self.assertEqual(self.post('auth/verify', {'token': raw}, {}).status_code, 204)
        self.assertEqual(self.post('auth/verify', {'token': raw}, {}).status_code, 400)
        headers = self.headers()
        raw = 'b' * 43
        ActionToken.objects.create(digest=digest(raw), purpose='RESET', user=self.user, email=self.user.email, portal='client', auth_version=self.user.auth_version, expires_at=timezone.now()+timedelta(hours=1))
        self.assertEqual(self.post('auth/reset', {'token': raw, 'password': 'Different-938-Synthetic!'}, {}).status_code, 204)
        self.assertEqual(self.client.get('/api/v1/mobile/dashboard', **headers).status_code, 401)

    @override_settings(IDENTITY_SHARED_PORTAL=True)
    def test_native_reset_cannot_switch_to_team_portal(self):
        lawyer = User.objects.create_user('reset-lawyer@example.test', PASSWORD, role='LAWYER')
        raw = 'c' * 43
        ActionToken.objects.create(digest=digest(raw), purpose='RESET', user=lawyer, email=lawyer.email, portal='team', auth_version=lawyer.auth_version, expires_at=timezone.now()+timedelta(hours=1))
        self.assertEqual(self.post('auth/reset', {'token': raw, 'password': 'Different-938-Synthetic!'}, {}).status_code, 400)
        lawyer.refresh_from_db(); self.assertTrue(lawyer.check_password(PASSWORD))
