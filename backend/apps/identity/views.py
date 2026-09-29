from django.conf import settings
from django.contrib.auth import authenticate, logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers as inputs
from .models import ActionToken, User
from .security import IdentityError, throttle
from .services import (audit, begin_challenge, complete_challenge, consume, enrollment,
                       establish_session, issue_token, locked_token, profile, validate_new_password)


class IdentityView(APIView):
    # CSRF é obrigatório inclusive em POST anônimo. Não usar a exceção de SessionAuthentication.
    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def data(self, request, serializer):
        value = serializer(data=request.data)
        value.is_valid(raise_exception=True)
        return value.validated_data

    def require_portal(self, request, portal):
        if request.portal != portal:
            raise IdentityError("FORBIDDEN", "Operação não disponível neste portal.", 403)

    def public_limit(self, request, scope, identity="", limit=5):
        # Limite agregado por portal + conta. Nunca confiar em X-Forwarded-For do navegador.
        throttle("global:" + scope, request.portal, 100)
        throttle(scope, identity or request.portal, limit)


class PublicView(IdentityView):
    authentication_classes = []
    permission_classes = [AllowAny]


class CSRFView(PublicView):
    def get(self, request):
        return Response({"csrfToken": get_token(request), "portal": request.portal,
                         "policyVersion": settings.REGISTRATION_POLICY_VERSION})


class RegisterView(PublicView):
    def post(self, request):
        self.require_portal(request, "client")
        data = self.data(request, inputs.RegisterSerializer)
        self.public_limit(request, "register", data["email"])
        if data["policyVersion"] != settings.REGISTRATION_POLICY_VERSION:
            raise IdentityError("POLICY_CHANGED", "Atualize a página para revisar o aviso vigente.")
        user = User(email=data["email"], first_name=data["name"], accepted_policy_version=data["policyVersion"])
        validate_new_password(data["password"], user)
        user.set_password(data["password"])
        try:
            with transaction.atomic():
                if not User.objects.filter(email__iexact=data["email"]).exists():
                    user.save()
                    issue_token("VERIFY", user.email, "client", user)
                    audit(user, "REGISTER", "client", policyVersion=data["policyVersion"])
        except IntegrityError:
            # Cadastro concorrente não enumera conta nem sobrescreve identidade.
            pass
        return Response({"message": "Se o cadastro puder ser concluído, você receberá um e-mail."}, status=202)


class VerifyView(PublicView):
    def post(self, request):
        self.require_portal(request, "client")
        data = self.data(request, inputs.TokenSerializer)
        self.public_limit(request, "verify", limit=30)
        with transaction.atomic():
            token = locked_token(data["token"], "VERIFY", "client")
            user = User.objects.select_for_update().get(pk=token.user_id)
            if not user.is_active or user.role != User.Role.CLIENT or user.auth_version != token.auth_version:
                raise IdentityError("INVALID_TOKEN", "Link inválido ou expirado.")
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
            consume(token)
            audit(user, "EMAIL_VERIFIED", "client")
        return Response(status=204)


class ResendView(PublicView):
    def post(self, request):
        self.require_portal(request, "client")
        data = self.data(request, inputs.EmailSerializer)
        self.public_limit(request, "resend", data["email"], limit=3)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=data["email"], role=User.Role.CLIENT, is_active=True, email_verified_at__isnull=True).first()
            if user:
                ActionToken.objects.filter(user=user, purpose="VERIFY", consumed_at__isnull=True).update(consumed_at=timezone.now())
                issue_token("VERIFY", user.email, "client", user)
        return Response({"message": "Se houver cadastro aguardando confirmação, enviaremos um novo link."}, status=202)


class LoginView(PublicView):
    def post(self, request):
        data = self.data(request, inputs.LoginSerializer)
        self.public_limit(request, "login", data["email"], limit=10)
        user = authenticate(request, username=data["email"], password=data["password"])
        if not user:
            raise IdentityError("INVALID_CREDENTIALS", "Não foi possível entrar com os dados informados.", 403)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            expected = "client" if user.role == User.Role.CLIENT else "team"
            # Revalidar senha sob lock: reset concorrente não pode conceder sessão antiga.
            if not user.is_active or not user.email_verified_at or expected != request.portal or not user.check_password(data["password"]):
                raise IdentityError("INVALID_CREDENTIALS", "Não foi possível entrar com os dados informados.", 403)
            if expected == "team":
                return Response(begin_challenge(request, user), status=202)
            establish_session(request, user)
            return Response({"user": profile(user)})


class EnrollView(PublicView):
    def post(self, request):
        self.public_limit(request, "enroll", request.session.get("challenge", {}).get("user_id", ""), limit=10)
        return Response(enrollment(request))


class MFAView(PublicView):
    def post(self, request):
        data = self.data(request, inputs.CodeSerializer)
        self.public_limit(request, "mfa", request.session.get("challenge", {}).get("user_id", ""))
        return Response(complete_challenge(request, data["code"]))


class RecoveryView(PublicView):
    def post(self, request):
        data = self.data(request, inputs.EmailSerializer)
        self.public_limit(request, "recovery", data["email"], limit=3)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=data["email"], is_active=True, email_verified_at__isnull=False).first()
            if user and ("client" if user.role == User.Role.CLIENT else "team") == request.portal:
                ActionToken.objects.filter(user=user, purpose="RESET", consumed_at__isnull=True).update(consumed_at=timezone.now())
                issue_token("RESET", user.email, request.portal, user)
        return Response({"message": "Se houver uma conta elegível, enviaremos as instruções por e-mail."}, status=202)


class ResetView(PublicView):
    def post(self, request):
        data = self.data(request, inputs.ResetSerializer)
        self.public_limit(request, "reset", limit=30)
        with transaction.atomic():
            token = locked_token(data["token"], "RESET", request.portal)
            user = User.objects.select_for_update().get(pk=token.user_id)
            if not user.is_active or user.auth_version != token.auth_version:
                raise IdentityError("INVALID_TOKEN", "Link inválido ou expirado.")
            validate_new_password(data["password"], user)
            user.set_password(data["password"])
            user.auth_version += 1
            user.save(update_fields=["password", "auth_version"])
            consume(token)
            audit(user, "PASSWORD_RESET", request.portal)
        request.session.flush()
        return Response(status=204)


class InviteView(IdentityView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        self.require_portal(request, "team")
        if request.user.role != User.Role.ADMIN:
            raise IdentityError("FORBIDDEN", "Somente a administração pode convidar profissionais.", 403)
        data = self.data(request, inputs.EmailSerializer)
        self.public_limit(request, "invite", str(request.user.pk), limit=10)
        with transaction.atomic():
            # Serializar convites do mesmo administrador; aceitação também verifica unicidade.
            User.objects.select_for_update().get(pk=request.user.pk)
            if not User.objects.filter(email__iexact=data["email"]).exists():
                ActionToken.objects.filter(email=data["email"], purpose="INVITE", consumed_at__isnull=True).update(consumed_at=timezone.now())
                issue_token("INVITE", data["email"], "team", created_by=request.user)
                audit(request.user, "INVITATION_CREATED", "team")
        return Response({"message": "Se o endereço for elegível, o convite será enviado."}, status=202)


class AcceptInviteView(PublicView):
    def post(self, request):
        self.require_portal(request, "team")
        data = self.data(request, inputs.AcceptInviteSerializer)
        self.public_limit(request, "accept-invite", limit=20)
        try:
            with transaction.atomic():
                token = locked_token(data["token"], "INVITE", "team")
                inviter = User.objects.filter(pk=token.created_by_id, is_active=True, role=User.Role.ADMIN).first()
                if not inviter or User.objects.filter(email__iexact=token.email).exists():
                    raise IdentityError("INVALID_TOKEN", "Convite inválido ou indisponível.")
                user = User(email=token.email, first_name=data["name"], role=User.Role.LAWYER, email_verified_at=timezone.now())
                validate_new_password(data["password"], user)
                user.set_password(data["password"])
                user.save()
                consume(token)
                audit(user, "INVITATION_ACCEPTED", "team")
        except IntegrityError as exc:
            raise IdentityError("INVALID_TOKEN", "Convite inválido ou indisponível.") from exc
        return Response({"message": "Conta profissional criada. Entre para configurar o segundo fator."}, status=201)


class MeView(IdentityView):
    def patch(self, request):
        data = self.data(request, inputs.ProfileSerializer)
        throttle("profile", str(request.user.pk), 20)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            user.first_name = data["name"]
            user.case_email_enabled = data["caseEmailEnabled"]
            user.save(update_fields=["first_name", "case_email_enabled"])
            audit(user, "PROFILE_UPDATED", request.portal)
        return Response({"user": profile(user)})

    def get(self, request):
        return Response({"user": profile(request.user), "portal": request.portal})


class LogoutView(IdentityView):
    def post(self, request):
        audit(request.user, "LOGOUT", request.portal)
        logout(request)
        return Response(status=204)


class ClientDashboardView(IdentityView):
    def get(self, request):
        self.require_portal(request, "client")
        return Response({"user": profile(request.user), "portal": "client", "caseManagementAvailable": True})


class TeamDashboardView(IdentityView):
    def get(self, request):
        self.require_portal(request, "team")
        return Response({"user": profile(request.user), "portal": "team", "caseManagementAvailable": True})
