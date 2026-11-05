from django.db import transaction
from django.db.models import F, Q, Count
from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response
from apps.identity.models import ActionToken, IdentityAudit
from django.utils import timezone
from apps.cases.views import CaseView
from apps.identity.models import User
from apps.identity.serializers import StrictSerializer
from apps.identity.security import IdentityError
from apps.identity.services import audit
class AccessInput(StrictSerializer):
    active = serializers.BooleanField()
    version = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=10, max_length=1000)
def serialize(user):
    return {"id": str(user.pk), "name": user.first_name, "email": user.email, "role": user.role,
            "active": user.is_active, "version": user.auth_version,
            "activated": user.email_verified_at is not None}
class UsersView(CaseView):
    def get(self, request):
        self.role(request, "ADMIN")
        query = User.objects.all()
        active = Q(is_active=True, email_verified_at__isnull=False)
        summary = query.aggregate(total=Count("pk"),
            lawyers=Count("pk", filter=Q(role="LAWYER") & active),
            clients=Count("pk", filter=Q(role="CLIENT") & active),
            pending=Count("pk", filter=Q(is_active=True, email_verified_at__isnull=True)),
            revoked=Count("pk", filter=Q(is_active=False)))
        role = request.query_params.get("role", "")
        status = request.query_params.get("status", "")
        search = request.query_params.get("search", "").strip()
        if role and role not in User.Role.values:
            raise IdentityError("INVALID_INPUT", "Perfil desconhecido.")
        if status not in ("", "active", "pending", "revoked") or len(search) > 150:
            raise IdentityError("INVALID_INPUT", "Filtro inválido.")
        if role: query = query.filter(role=role)
        if status == "active": query = query.filter(active)
        if status == "pending": query = query.filter(is_active=True, email_verified_at__isnull=True)
        if status == "revoked": query = query.filter(is_active=False)
        if search: query = query.filter(Q(first_name__icontains=search) | Q(email__icontains=search))
        response = self.listed(request, query.annotate(created_at=F("date_joined")), serialize)
        response.data.update(summary=summary, total=query.count())
        return response
class UserAccessView(CaseView):
    def post(self, request, pk):
        self.role(request, "ADMIN")
        self.limited(request)
        data = self.data(request, AccessInput)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(pk=pk).first()
            if not user: raise Http404
            if user.role == "ADMIN": raise IdentityError("FORBIDDEN", "Contas administrativas exigem gestão operacional.", 403)
            if user.auth_version != data["version"]: raise IdentityError("CONFLICT", "Atualize a lista antes de continuar.", 409)
            user.is_active = data["active"]
            user.auth_version += 1
            user.save(update_fields=["is_active", "auth_version"])
            ActionToken.objects.filter(user=user, consumed_at__isnull=True).update(consumed_at=timezone.now())
            audit(request.user, "USER_ACCESS_CHANGED", request.portal, targetId=str(user.pk), active=user.is_active, reason=data["reason"])
        return Response(serialize(user))


class UserDetailsView(CaseView):
    def get(self, request, pk):
        self.role(request, "ADMIN")
        user = User.objects.filter(pk=pk).first()
        if not user:
            raise Http404
        from apps.billing.models import Membership
        from apps.billing.provider import environment
        from apps.billing.services import active_memberships
        membership = None
        if user.role == "CLIENT":
            now = timezone.now()
            current = active_memberships(user).select_related("order").order_by("-expires_at").first()
            latest = current or Membership.objects.filter(user=user, order__environment=environment()).select_related("order").order_by("-expires_at").first()
            status = "NONE"
            if latest:
                status = "ACTIVE" if current else "REVOKED" if latest.revoked_at or latest.order.status != "PAID" else "UPCOMING" if latest.starts_at > now else "EXPIRED"
            membership = {"status": status, "environment": environment(),
                "startsAt": latest.starts_at.isoformat() if latest else None,
                "expiresAt": latest.expires_at.isoformat() if latest else None}
        events = IdentityAudit.objects.filter(action="USER_ACCESS_CHANGED", metadata__targetId=str(pk)).select_related("actor")
        response = self.listed(request, events, lambda event: {
            "id": str(event.pk), "createdAt": event.created_at.isoformat(),
            "active": event.metadata.get("active"), "reason": event.metadata.get("reason", ""),
            "actor": event.actor.email if event.actor else "Administrador indisponível"})
        response.data.update(user=serialize(user), joinedAt=user.date_joined.isoformat(), membership=membership)
        return response
