from datetime import timedelta
from uuid import uuid4

from django.test import Client, TestCase
from django.utils import timezone

from apps.cases.models import Case, CaseEvent
from apps.communication.models import Message
from apps.identity.models import User
from apps.legal.proposals import publish_proposal
from . import test_mobile as mobile


class ChannelContractTests(TestCase):
    setUp = mobile.MobileTests.setUp
    login = mobile.MobileTests.login
    headers = mobile.MobileTests.headers

    def channels(self):
        headers = self.headers()
        browser = Client(enforce_csrf_checks=True, **self.client.defaults)
        csrf = browser.get('/api/v1/auth/csrf').json()['csrfToken']
        response = browser.post('/api/v1/auth/login',
            {'email': self.user.email, 'password': mobile.PASSWORD},
            content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200, response.content)
        return browser, headers

    def compare(self, browser, headers, path):
        web = browser.get('/api/v1/' + path)
        native = self.client.get('/api/v1/mobile/' + path, **headers)
        self.assertEqual(web.status_code, 200, web.content)
        self.assertEqual(native.status_code, 200, native.content)
        self.assertEqual(web.json(), native.json())
        return web.json()

    def fixture(self):
        lawyer = User.objects.create_user('channel-lawyer@example.test', None, role='LAWYER')
        case = Case.objects.create(owner=self.user, lawyer=lawyer, state=Case.State.TRIAGE, version=2,
                                   title='Shared case', description='Client narrative')
        for public in (True, False):
            CaseEvent.objects.create(case=case, actor=lawyer, action='TRIAGE_STARTED',
                state=case.state, version=1 if public else 2, public=public,
                reason='Public event' if public else 'Internal event')
            Message.objects.create(case=case, author=lawyer, client_id=uuid4(),
                visibility='PUBLIC' if public else 'INTERNAL', text='Public text' if public else 'Internal text')
        proposal = publish_proposal(lawyer, case.pk, 2, scope='Defense', fee_cents=120000,
            expenses='Separate', payment_terms='Separate agreement',
            valid_until=timezone.now() + timedelta(days=7))
        return case, proposal

    def test_read_contracts_and_private_content_are_equal_across_channels(self):
        case, proposal = self.fixture()
        browser, headers = self.channels()
        self.compare(browser, headers, 'cases')
        base = f'cases/{case.pk}'
        for suffix in ('timeline', 'messages', 'proposals'):
            data = self.compare(browser, headers, base + '/' + suffix)
            self.assertNotIn('Internal', str(data))
        detail = self.client.get('/api/v1/mobile/' + base, **headers).json()
        self.assertTrue(detail.pop('canMessage'))
        self.assertEqual(detail, browser.get('/api/v1/' + base).json())
        dashboard = self.client.get('/api/v1/mobile/dashboard', **headers).json()
        self.assertEqual(dashboard.pop('user'), browser.get('/api/v1/me').json()['user'])
        self.assertEqual(dashboard.pop('membership'), {'active': False, 'expiresAt': None})
        self.assertEqual(dashboard, browser.get('/api/v1/dashboard/overview').json())

    def test_decision_retry_between_channels_is_idempotent(self):
        case, proposal = self.fixture()
        browser, headers = self.channels()
        path = f'cases/{case.pk}/proposals/{proposal.pk}/decision'
        payload = {'version': 3, 'accepted': True}
        first = self.client.post('/api/v1/mobile/' + path, payload,
            content_type='application/json', **headers)
        csrf = browser.get('/api/v1/auth/csrf').json()['csrfToken']
        retry = browser.post('/api/v1/' + path, payload,
            content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(retry.status_code, 200, retry.content)
        self.assertEqual(first.json(), retry.json())
        self.assertEqual(CaseEvent.objects.filter(case=case, action='PROPOSAL_ACCEPTED').count(), 1)
        self.compare(browser, headers, f'cases/{case.pk}/proposals')

    def test_ownership_change_revokes_both_channels(self):
        case, proposal = self.fixture()
        browser, headers = self.channels()
        other = User.objects.create_user('channel-other@example.test', None)
        Case.objects.filter(pk=case.pk).update(owner=other)
        for suffix in ('', '/timeline', '/messages', '/proposals'):
            path = f'cases/{case.pk}' + suffix
            with self.subTest(path=path):
                self.assertEqual(browser.get('/api/v1/' + path).status_code, 404)
                self.assertEqual(self.client.get('/api/v1/mobile/' + path, **headers).status_code, 404)
        self.assertEqual(self.compare(browser, headers, 'cases')['results'], [])
