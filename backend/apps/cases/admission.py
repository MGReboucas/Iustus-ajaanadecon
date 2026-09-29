from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from apps.identity.models import User
from apps.identity.serializers import StrictSerializer
from apps.identity.services import audit
from apps.identity.security import IdentityError
from .models import ServiceAccess
from .views import CaseView

class AccessInput(StrictSerializer):
    email = serializers.EmailField()
    enabled = serializers.BooleanField()
    expiresAt = serializers.DateTimeField(required=False)
    reason = serializers.CharField(min_length=5, max_length=240)

class AccessView(CaseView):
    def get(self, request):
        self.role(request, "ADMIN")
        return self.listed(request, ServiceAccess.objects.select_related("user").annotate(created_at=F("updated_at")),
            lambda row: {"email": row.user.email, "enabled": row.enabled,
                         "expiresAt": row.expires_at.isoformat(), "reason": row.reason})

    def post(self, request):
        self.role(request, "ADMIN")
        self.limited(request)
        data = self.data(request, AccessInput)
        if data["enabled"] and (not data.get("expiresAt") or data["expiresAt"] <= timezone.now()):
            raise IdentityError("INVALID_EXPIRATION", "Informe uma validade futura para a liberação.", 422)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=data["email"].lower(), role="CLIENT",
                is_active=True, email_verified_at__isnull=False).first()
            if not user:
                raise Http404
            access, _ = ServiceAccess.objects.update_or_create(user=user, defaults={
                "enabled": data["enabled"], "expires_at": data.get("expiresAt", timezone.now()),
                "reason": data["reason"], "granted_by": request.user})
            audit(request.user, "service.access_changed", request.portal, userId=str(user.pk),
                  enabled=access.enabled, expiresAt=access.expires_at.isoformat(), reason=access.reason)
        return Response({"message": "Liberação atualizada. Casos já enviados permanecem em acompanhamento."})
