from django.http import JsonResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from apps.identity.middleware import PortalMiddleware


@override_settings(IDENTITY_SHARED_PORTAL=True, ALLOWED_HOSTS=["backend.test"],
                   PORTAL_ORIGINS={"client": "https://old.example", "team": "https://old.example"},
                   IUSTUS_PORTAL_ALIASES=["https://iustus.app", "https://www.iustus.app"])
class PortalAliasTests(SimpleTestCase):
    def call(self, host, secret="test-proxy-only", path="/api/v1/billing/plan"):
        request = RequestFactory().get(path, HTTP_HOST="backend.test",
                                      HTTP_X_IUSTUS_PORTAL_HOST=host,
                                      HTTP_X_IUSTUS_PROXY_KEY=secret)
        response = PortalMiddleware(lambda req: JsonResponse({"portal": req.portal}))(request)
        return response, request

    def test_official_hosts_route_to_shared_portal(self):
        for host in ["iustus.app", "www.iustus.app", "old.example"]:
            response, request = self.call(host)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(request.portal, "client")
            self.assertEqual(request.META["HTTP_HOST"], host)
            self.assertEqual(request.META["HTTP_X_FORWARDED_PROTO"], "https")

    def test_alias_preserves_team_mfa_routing(self):
        response, request = self.call("www.iustus.app", path="/api/v1/auth/mfa/verify")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.portal, "team")

    def test_untrusted_hosts_and_proxy_remain_blocked(self):
        for host in ["evil.example", "iustus.app.evil.example", "iustus.app:1234"]:
            self.assertEqual(self.call(host)[0].status_code, 403)
        self.assertEqual(self.call("iustus.app", secret="wrong")[0].status_code, 403)

    @override_settings(IDENTITY_SHARED_PORTAL=False)
    def test_alias_not_enabled_for_separate_portals(self):
        self.assertEqual(self.call("iustus.app")[0].status_code, 403)
