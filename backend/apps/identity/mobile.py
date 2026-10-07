"""API nativa do associado, sem autenticação por cookies ou segredos no aplicativo."""
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.services import membership_data
from apps.legal.proposal_views import ProposalsView, ProposalDecisionView
from apps.cases.models import Case
from apps.cases.services import accessible, case_data, get_case
from apps.cases.views import CaseView, TimelineView
from apps.communication.views import MessagesView, OverviewView
from .models import ActionToken, MobileSession, User
from .security import IdentityError, digest, throttle
from .serializers import EmailSerializer, LoginSerializer
from .services import audit, issue_token, profile


class MobileAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != b"bearer" or not re.fullmatch(rb"[A-Za-z0-9_-]{43}", header[1]):
            raise IdentityError("AUTH_REQUIRED", "Entre novamente para continuar.", 401)
        now = timezone.now()
        session = MobileSession.objects.select_related("user").filter(digest=digest(header[1].decode("ascii"))).first()
        if not session:
            raise IdentityError("AUTH_REQUIRED", "Entre novamente para continuar.", 401)
        user = session.user
        valid = (user.is_active and user.email_verified_at and user.role == User.Role.CLIENT
                 and session.auth_version == user.auth_version and session.expires_at > now
                 and session.last_active_at > now - timedelta(seconds=settings.IDENTITY_IDLE_SECONDS["client"]))
        if not valid:
            MobileSession.objects.filter(pk=session.pk).delete()
            raise IdentityError("AUTH_REQUIRED", "Sua sessão expirou. Entre novamente.", 401)
        # Não recriar sessão removida por logout concorrente.
        if not MobileSession.objects.filter(pk=session.pk).update(last_active_at=now):
            raise IdentityError("AUTH_REQUIRED", "Entre novamente para continuar.", 401)
        return user, session


class MobileView(APIView):
    authentication_classes = [MobileAuthentication]
    permission_classes = [IsAuthenticated]
    listed = CaseView.listed

    @method_decorator(sensitive_post_parameters())
    def dispatch(self, request, *args, **kwargs):
        # Bearer explícito: cookies nunca autenticam estas rotas. As rotas web
        # continuam com CSRF obrigatório. O proxy privado permanece obrigatório.
        return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        if request.portal != "client":
            raise IdentityError("FORBIDDEN", "Aplicativo disponível no portal do associado.", 403)
        super().initial(request, *args, **kwargs)

    def validated(self, request, serializer):
        value = serializer(data=request.data)
        value.is_valid(raise_exception=True)
        return value.validated_data

    def limit(self, scope, identity, limit):
        # Compartilha os limites por conta com o login e recuperação da web.
        throttle("global:" + scope, "client", 100)
        throttle(scope, identity, limit)


class MobilePublicView(MobileView):
    authentication_classes = []
    permission_classes = [AllowAny]


class MobileLoginView(MobilePublicView):
    def post(self, request):
        data = self.validated(request, LoginSerializer)
        self.limit("login", data["email"], 10)
        user = authenticate(request, username=data["email"], password=data["password"])
        if not user:
            raise IdentityError("INVALID_CREDENTIALS", "Não foi possível entrar com os dados informados.", 403)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            if not user.is_active or not user.email_verified_at or user.role != User.Role.CLIENT or not user.check_password(data["password"]):
                raise IdentityError("INVALID_CREDENTIALS", "Não foi possível entrar com os dados informados.", 403)
            now = timezone.now()
            MobileSession.objects.filter(user=user, expires_at__lte=now).delete()
            # Limita o número de sessões por conta; login novo remove as antigas.
            stale = list(MobileSession.objects.filter(user=user).order_by("-created_at").values_list("pk", flat=True)[4:])
            MobileSession.objects.filter(pk__in=stale).delete()
            raw = secrets.token_urlsafe(32)
            expires = now + timedelta(seconds=settings.IDENTITY_SESSION_SECONDS["client"])
            MobileSession.objects.create(digest=digest(raw), user=user, auth_version=user.auth_version,
                                         expires_at=expires, last_active_at=now)
            audit(user, "MOBILE_LOGIN", "client")
        return Response({"token": raw, "expiresAt": expires.isoformat(), "user": profile(user)})


class MobileRecoveryView(MobilePublicView):
    def post(self, request):
        data = self.validated(request, EmailSerializer)
        self.limit("recovery", data["email"], 3)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=data["email"], role=User.Role.CLIENT,
                is_active=True, email_verified_at__isnull=False).first()
            if user:
                ActionToken.objects.filter(user=user, purpose="RESET", consumed_at__isnull=True).update(consumed_at=timezone.now())
                issue_token("RESET", user.email, "client", user)
        return Response({"message": "Se houver uma conta elegível, enviaremos as instruções por e-mail."}, status=202)


class MobileLogoutView(MobileView):
    def post(self, request):
        MobileSession.objects.filter(pk=request.auth.pk).delete()
        audit(request.user, "MOBILE_LOGOUT", "client")
        return Response(status=204)


class MobileDashboardView(MobileView):
    def get(self, request):
        result = OverviewView.get(self, request).data
        return Response({**result, "user": profile(request.user), "membership": membership_data(request.user)})


class MobileCasesView(MobileView):
    def get(self, request):
        return self.listed(request, accessible(request.user), case_data)


class MobileCaseView(MobileView):
    def get(self, request, case_id):
        item = get_case(request.user, case_id)
        return Response({**case_data(item, detail=True), "canMessage": bool(item.lawyer_id)
                         and item.state not in (Case.State.DRAFT, Case.State.REJECTED, Case.State.CLOSED)})


class MobileTimelineView(MobileView):
    def get(self, request, case_id):
        return TimelineView.get(self, request, case_id)


class MobileMessagesView(MobileView):
    role = CaseView.role
    limited = CaseView.limited
    data = MobileView.validated
    get = MessagesView.get
    post = MessagesView.post




class MobileProposalsView(MobileView):
    get = ProposalsView.get


class MobileProposalDecisionView(MobileView):
    limited = CaseView.limited
    data = MobileView.validated
    post = ProposalDecisionView.post
