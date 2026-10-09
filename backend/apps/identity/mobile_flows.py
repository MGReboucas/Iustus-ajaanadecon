"""Client-only native adapters. Business rules remain in the shared web services."""
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.response import Response

from apps.cases import views as cases
from apps.documents import views as documents
from apps.legal.views import WorkflowView
from apps.privacy.views import RequestsView as PrivacyView
from apps.communication.views import NotificationsView, NotificationReadView
from apps.billing.views import ActivateView, ResendAccessView, PlanView
from integrations.storage.private import open_object
from . import views as identity
from .services import audit
from .models import ActionToken
from .security import IdentityError, digest
from .mobile import MobileView, MobilePublicView


class PublicAdapter(MobilePublicView):
    data = MobileView.validated
    require_portal = identity.IdentityView.require_portal
    public_limit = identity.IdentityView.public_limit


class ContextView(PublicAdapter):
    def get(self, request):
        return Response({"policyVersion": settings.REGISTRATION_POLICY_VERSION,
                         "registrationAvailable": not settings.MEMBERSHIP_REQUIRED,
                         "billingAvailable": settings.BILLING_ENABLED,
                         "checkoutAvailable": getattr(settings, "MOBILE_EXTERNAL_CHECKOUT_ENABLED", False)})


class RegisterView(PublicAdapter):
    post = identity.RegisterView.post


class VerifyView(PublicAdapter):
    post = identity.VerifyView.post


class ResendView(PublicAdapter):
    post = identity.ResendView.post


class ResetView(PublicAdapter):
    def post(self, request):
        from .serializers import ResetSerializer
        data = self.data(request, ResetSerializer)
        candidate = ActionToken.objects.filter(digest=digest(data["token"]), purpose="RESET").select_related("user").first()
        if candidate and (candidate.portal != "client" or not candidate.user or candidate.user.role != "CLIENT"):
            raise IdentityError("INVALID_TOKEN", "Link inválido ou expirado.")
        return identity.ResetView.post(self, request)


class MemberActivateView(PublicAdapter):
    post = ActivateView.post


class MemberResendView(PublicAdapter):
    post = ResendAccessView.post


class MobilePlanView(PublicAdapter):
    get = PlanView.get


class ProfileView(MobileView):
    patch = identity.MeView.patch


class CatalogView(MobileView):
    get = cases.CatalogView.get


class SubmitView(MobileView):
    post = cases.SubmitView.post


class RequestsView(MobileView):
    get = cases.RequestsView.get


class RespondView(MobileView):
    def post(self, request, case_id, request_id):
        return cases.RequestActionView.post(self, request, case_id, request_id, "response")


class WorkView(MobileView):
    get = WorkflowView.get
    post = WorkflowView.post  # shared role check permits only SIGN for clients


class DocumentsView(MobileView):
    get = documents.DocumentsView.get

    def post(self, request, case_id):
        response = documents.DocumentsView.post(self, request, case_id)
        response.data["uploadUrl"] = f"/api/v1/mobile/uploads/{response.data['uploadId']}/content"
        return response


class VersionsView(MobileView):
    def post(self, request, document_id):
        response = documents.VersionsView.post(self, request, document_id)
        response.data["uploadUrl"] = f"/api/v1/mobile/uploads/{response.data['uploadId']}/content"
        return response


class UploadContentView(MobileView):
    post = documents.ContentView.post


class AuthorizeView(MobileView):
    post = documents.AuthorizeUploadView.post


class CompleteView(MobileView):
    post = documents.CompleteView.post


class DownloadView(MobileView):
    def get(self, request, document_id, version_id):
        # Native downloads authenticate each request with Bearer, never URL tokens
        # or the web session's signed download capability.
        item = documents.downloadable(request, document_id, version_id)
        try:
            source = open_object(item.object_key)
        except FileNotFoundError:
            raise Http404
        audit(request.user, "DOCUMENT_DOWNLOADED", request.portal, versionId=str(item.pk))
        response = FileResponse(source, as_attachment=True, filename=item.filename, content_type="application/octet-stream")
        response["Cache-Control"] = "no-store, private"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox"
        return response


class PrivacyRequestsView(MobileView):
    get = PrivacyView.get
    post = PrivacyView.post


class NoticesView(MobileView):
    get = NotificationsView.get


class ReadNoticeView(MobileView):
    post = NotificationReadView.post
