import secrets
import time
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ActionToken, IdentityAudit, IdentityEmail, MFADevice, User
from .security import IdentityError, decrypt, digest, encrypt, recovery_codes


def audit(user, action, portal, **metadata):
    IdentityAudit.objects.create(actor=user, action=action, portal=portal, metadata=metadata)


def validate_new_password(password, user):
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise IdentityError("INVALID_PASSWORD", " ".join(exc.messages)) from exc


def issue_token(purpose, email, portal, user=None, created_by=None):
    raw = secrets.token_urlsafe(32)
    hours = 1 if purpose == ActionToken.Purpose.RESET else 24
    ActionToken.objects.create(
        digest=digest(raw), purpose=purpose, user=user, email=email, portal=portal,
        auth_version=user.auth_version if user else 1, created_by=created_by,
        expires_at=timezone.now() + timedelta(hours=hours),
    )
    mode = {"VERIFY": "verify", "RESET": "reset", "INVITE": "invite"}[purpose]
    titles = {"VERIFY": "Confirme seu e-mail", "RESET": "Redefina sua senha", "INVITE": "Convite para a equipe Iustus"}
    # Fragmento evita incluir o token no request HTTP, Referer ou log do servidor web.
    url = f"{settings.PORTAL_ORIGINS[portal]}/acessar#{mode}={raw}"
    IdentityEmail.objects.create(
        recipient=email, subject=titles[purpose], available_at=timezone.now(),
        encrypted_body=encrypt(f"{titles[purpose]}\n\n{url}\n\nEste link expira em {hours} hora(s). Se não reconhece a solicitação, ignore esta mensagem."),
    )


def locked_token(raw, purpose, portal):
    """Chamador deve estar em transaction.atomic; consumir junto com a alteração."""
    candidate = ActionToken.objects.filter(digest=digest(raw), purpose=purpose, portal=portal).first()
    if candidate:
        # Ordem de locks única: usuário antes de token (também em reenvio/recuperação).
        owner = candidate.user_id or candidate.created_by_id
        if owner:
            User.objects.select_for_update().filter(pk=owner).first()
    token = ActionToken.objects.select_for_update().filter(digest=digest(raw), purpose=purpose, portal=portal).first()
    if not token or token.consumed_at or token.expires_at <= timezone.now():
        raise IdentityError("INVALID_TOKEN", "Link inválido, expirado ou já utilizado.")
    return token


def consume(token):
    token.consumed_at = timezone.now()
    token.save(update_fields=["consumed_at"])


def profile(user):
    return {"id": str(user.pk), "name": user.first_name, "email": user.email, "role": user.role, "caseEmailEnabled": user.case_email_enabled}


def establish_session(request, user, mfa=False):
    # Revalidar no lock do usuário antes de chamar esta função.
    request.session.flush()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    lifetime = settings.IDENTITY_SESSION_SECONDS[request.portal]
    request.session.update({
        "portal": request.portal, "auth_version": user.auth_version,
        "mfa_verified": mfa, "absolute_expiry": time.time() + lifetime,
        "last_active": time.time(),
    })
    request.session.set_expiry(lifetime)
    audit(user, "LOGIN", request.portal, mfa=mfa)


def begin_challenge(request, user):
    request.session.flush()
    request.session.cycle_key()
    device = MFADevice.objects.filter(user=user).first()
    enroll = device is None or device.confirmed_at is None
    request.session["challenge"] = {
        "user_id": str(user.pk), "version": user.auth_version, "portal": "team",
        "expires": time.time() + 300, "enroll": enroll,
    }
    request.session.set_expiry(300)
    return {"mfaRequired": True, "enrollmentRequired": enroll}


def challenge_user(request):
    challenge = request.session.get("challenge", {})
    if request.portal != "team" or challenge.get("portal") != "team" or challenge.get("expires", 0) <= time.time():
        raise IdentityError("CHALLENGE_EXPIRED", "Entre novamente para confirmar o segundo fator.", 403)
    user = User.objects.select_for_update().filter(pk=challenge.get("user_id"), is_active=True).first()
    if not user or user.role not in (User.Role.LAWYER, User.Role.ADMIN) or not user.email_verified_at or user.auth_version != challenge.get("version"):
        raise IdentityError("CHALLENGE_EXPIRED", "Entre novamente para confirmar o segundo fator.", 403)
    return user, challenge


def verify_factor(device, code, allow_recovery):
    """User e device devem estar bloqueados; contador impede reuso e corrida do OTP."""
    now = int(time.time())
    totp = pyotp.TOTP(decrypt(device.encrypted_secret))
    if len(code) == 6 and code.isdigit():
        for offset in (-1, 0, 1):
            moment = now + offset * 30
            counter = moment // 30
            if counter > device.last_counter and totp.verify(code, for_time=moment):
                device.last_counter = counter
                device.save(update_fields=["last_counter"])
                return True
    if allow_recovery:
        value = digest(code.replace(" ", "").lower())
        matching = next((entry for entry in device.recovery_hashes if secrets.compare_digest(entry, value)), None)
        if matching:
            device.recovery_hashes = [entry for entry in device.recovery_hashes if entry != matching]
            device.save(update_fields=["recovery_hashes"])
            return True
    return False


def enrollment(request):
    with transaction.atomic():
        user, challenge = challenge_user(request)
        device = MFADevice.objects.filter(user=user).first()
        if not challenge["enroll"] or (device and device.confirmed_at):
            raise IdentityError("MFA_ALREADY_CONFIGURED", "O segundo fator já está configurado.", 409)
        if not device:
            device = MFADevice.objects.create(user=user, encrypted_secret=encrypt(pyotp.random_base32()))
        secret = decrypt(device.encrypted_secret)
        return {"secret": secret, "uri": pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Iustus")}


def complete_challenge(request, code):
    with transaction.atomic():
        user, challenge = challenge_user(request)
        device = MFADevice.objects.select_for_update().filter(user=user).first()
        if not device or (challenge["enroll"] and device.confirmed_at):
            raise IdentityError("CHALLENGE_EXPIRED", "Entre novamente para confirmar o segundo fator.", 403)
        if not verify_factor(device, code, allow_recovery=not challenge["enroll"]):
            raise IdentityError("INVALID_MFA", "Código inválido ou já utilizado.", 403)
        codes = None
        if challenge["enroll"]:
            codes, hashes = recovery_codes()
            device.confirmed_at = timezone.now()
            device.recovery_hashes = hashes
            device.save(update_fields=["confirmed_at", "recovery_hashes"])
            audit(user, "MFA_ENROLLED", "team")
        establish_session(request, user, mfa=True)
        return {"user": profile(user), "recoveryCodes": codes}
