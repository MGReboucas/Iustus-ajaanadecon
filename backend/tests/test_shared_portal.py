from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.identity.models import User
from apps.cases.models import Case
from .test_identity import IdentityTests, PASSWORD

@override_settings(IDENTITY_SHARED_PORTAL=True, IDENTITY_MFA_REQUIRED=False,
    PORTAL_ORIGINS={'client':'http://localhost:3000','team':'http://localhost:3000'})
class SharedPortalTests(TestCase):
    browser=IdentityTests.browser
    post=IdentityTests.post
    user=IdentityTests.user
    login=IdentityTests.login
    email_token=IdentityTests.email_token

    def test_registration_verification_and_role_isolation(self):
        browser=self.browser()
        self.assertTrue(browser.get('/api/v1/auth/csrf').json()['registrationAvailable'])
        data={'email':'new@example.test','password':PASSWORD,'name':'Cliente Teste','policyVersion':'development-v1'}
        self.assertEqual(self.post(browser,'auth/register',{**data,'role':'ADMIN'}).status_code,400)
        self.assertEqual(self.post(browser,'auth/register',data).status_code,202)
        user=User.objects.get(email=data['email'])
        self.assertEqual(user.role,'CLIENT')
        self.assertEqual(self.login(browser,user).status_code,403)
        self.assertEqual(self.post(browser,'auth/verify',{'token':self.email_token('verify')}).status_code,204)
        self.assertEqual(self.login(browser,user).status_code,200)
        self.assertEqual(browser.get('/api/v1/dashboard/client').status_code,200)
        for route in ['dashboard/team','admin/users','admin/service-access','cases/lawyers']:
            self.assertEqual(browser.get('/api/v1/'+route).status_code,403,route)
        admin=self.user(role='ADMIN',email='admin@example.test')
        other=self.browser()
        self.assertEqual(self.login(other,admin).status_code,200)
        self.assertEqual(other.get('/api/v1/dashboard/team').status_code,200)
        self.assertEqual(other.get('/api/v1/dashboard/client').status_code,403)

    def test_password_recovery_for_both_profiles(self):
        for role in ['CLIENT','ADMIN']:
            user=self.user(role=role,email=role.lower()+'@example.test')
            browser=self.browser()
            self.assertEqual(self.post(browser,'auth/recovery',{'email':user.email}).status_code,202)
            token=self.email_token('reset')
            self.assertEqual(self.post(browser,'auth/reset',{'token':token,'password':PASSWORD+'New'}).status_code,204)
            self.assertEqual(self.post(browser,'auth/login',{'email':user.email,'password':PASSWORD+'New'}).status_code,200)

    def test_case_admission_assignment_and_tenant_isolation(self):
        owner=self.user(email='owner@example.test')
        unrelated=self.user(email='other@example.test')
        admin=self.user(role='ADMIN',email='admin@example.test')
        lawyer=self.user(role='LAWYER',email='lawyer@example.test')
        cb,ab,lb,ob=[self.browser() for _ in range(4)]
        for browser,user in [(cb,owner),(ab,admin),(lb,lawyer),(ob,unrelated)]:
            self.assertEqual(self.login(browser,user).status_code,200)
        data={'title':'Caso de teste','description':'Descricao sintetica suficientemente detalhada para triagem.','category':'CONSUMER','scopeAcknowledged':True}
        created=self.post(cb,'cases',data)
        self.assertEqual(created.status_code,201,created.content)
        item=created.json();route='cases/'+item['id']
        csrf=cb.get('/api/v1/auth/csrf').json()['csrfToken']
        self.assertEqual(cb.post('/api/v1/'+route+'/submit',{'version':item['version']},content_type='application/json',HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY='synthetic-submit-001').status_code,422)
        grant=self.post(ab,'admin/service-access',{'email':owner.email,'enabled':True,'expiresAt':(timezone.now()+timedelta(days=1)).isoformat(),'reason':'Atendimento de teste autorizado'})
        self.assertEqual(grant.status_code,200,grant.content)
        sent=cb.post('/api/v1/'+route+'/submit',{'version':item['version']},content_type='application/json',HTTP_X_CSRFTOKEN=csrf,HTTP_IDEMPOTENCY_KEY='synthetic-submit-002')
        self.assertEqual(sent.status_code,200,sent.content)
        assigned=self.post(ab,route+'/assignment',{'version':sent.json()['version'],'lawyerId':str(lawyer.pk),'reason':'Distribuicao para teste'})
        self.assertEqual(assigned.status_code,200,assigned.content)
        self.assertEqual(lb.get('/api/v1/'+route).status_code,200)
        self.assertEqual(ob.get('/api/v1/'+route).status_code,404)
        self.assertEqual(ab.get('/api/v1/'+route).status_code,404)
        triage=self.post(lb,route+'/transitions',{'version':assigned.json()['version'],'targetState':'EM_TRIAGEM'})
        self.assertEqual(triage.status_code,200,triage.content)

    def test_public_registration_does_not_inherit_signed_in_admin_role(self):
        browser=self.browser()
        admin=self.user(role='ADMIN',email='admin@example.test')
        self.login(browser,admin)
        response=self.post(browser,'auth/register',{'email':'new@example.test','name':'Cliente Novo','password':PASSWORD,'policyVersion':'development-v1'})
        self.assertEqual(response.status_code,202)
        self.assertEqual(User.objects.get(email='new@example.test').role,'CLIENT')
        self.assertEqual(self.post(browser,'auth/verify',{'token':self.email_token('verify')}).status_code,204)
        self.assertEqual(browser.get('/api/v1/dashboard/team').status_code,200)
