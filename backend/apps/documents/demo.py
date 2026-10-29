"""Restricted synthetic-file demonstration; never marks documents as scanned."""
from django.conf import settings
from apps.identity.security import IdentityError


def demo_user(user):
    return settings.DOCUMENT_DEMO_ENABLED and user.email.lower() in settings.DOCUMENT_DEMO_EMAILS


def require_demo_access(user, case):
    if not demo_user(user) or not demo_user(case.owner):
        raise IdentityError("DEMO_RESTRICTED", "Envio de demonstração restrito às contas de teste autorizadas.", 403)


def guard_demo(user, case, item=None):
    if settings.DOCUMENT_DEMO_ENABLED or (item and item.status == "DEMO_UNVERIFIED"):
        require_demo_access(user, case)
