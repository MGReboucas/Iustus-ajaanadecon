import secrets
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse


def error_response(code, message, status=403):
    return JsonResponse({"error": {"code": code, "message": message, "fields": {}}}, status=status)


def csrf_failure(request, reason=""):
    return error_response("CSRF_FAILED", "Atualize a página e tente novamente.")


class PortalMiddleware:
    """O proxy local encaminha Host original e prova sua identidade com segredo privado."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.portal = None
        if request.path.startswith("/api/v1/") and request.path != "/api/v1/health/":
            supplied = request.META.get("HTTP_X_IUSTUS_PROXY_KEY", "")
            if not supplied or not secrets.compare_digest(supplied, settings.IUSTUS_PROXY_SECRET):
                return self.finish(error_response("UNTRUSTED_PROXY", "Acesso indisponível por esta origem."))
            # get_host também aplica ALLOWED_HOSTS. X-Forwarded-Host nunca escolhe o portal.
            original_host = request.get_host().lower()
            host = request.META.get("HTTP_X_IUSTUS_PORTAL_HOST", original_host).lower()
            origins = {urlsplit(origin).netloc.lower(): role for role, origin in settings.PORTAL_ORIGINS.items()}
            request.portal = origins.get(host)
            if not request.portal:
                return self.finish(error_response("INVALID_PORTAL", "Portal não permitido."))
            request.META["HTTP_HOST"] = host
            expected_scheme = urlsplit(settings.PORTAL_ORIGINS[request.portal]).scheme
            request.META["HTTP_X_FORWARDED_PROTO"] = expected_scheme
        response = self.get_response(request)
        return self.finish(response) if request.path.startswith("/api/v1/") else response

    @staticmethod
    def finish(response):
        response["Cache-Control"] = "no-store, private"
        response["Referrer-Policy"] = "no-referrer"
        return response


class SessionBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.portal and request.user.is_authenticated:
            user, session = request.user, request.session
            now = time.time()
            expected = "client" if user.role == "CLIENT" else "team"
            valid = (
                session.get("portal") == request.portal == expected
                and session.get("auth_version") == user.auth_version
                and user.email_verified_at is not None
                and user.is_active
                and now < session.get("absolute_expiry", 0)
                and now - session.get("last_active", 0) < settings.IDENTITY_IDLE_SECONDS[expected]
                and (expected == "client" or not settings.IDENTITY_MFA_REQUIRED or session.get("mfa_verified") is True)
            )
            if not valid:
                # Não apagar a sessão válida do outro portal em uma tentativa de replay.
                if session.get("portal") == request.portal:
                    logout(request)
                    if request.path.startswith("/api/v1/auth/"):
                        return self.get_response(request)
                return error_response("AUTH_REQUIRED", "Sua sessão não é válida neste portal.")
            session["last_active"] = now
        return self.get_response(request)
