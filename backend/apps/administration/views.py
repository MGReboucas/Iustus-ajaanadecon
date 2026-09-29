from django.db import transaction
from django.db.models import F
from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response
from apps.cases.models import Case
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
            "active": user.is_active, "version": user.auth_version}
class UsersView(CaseView):
    def get(self, request):
        self.role(request, "ADMIN")
        return self.listed(request, User.objects.annotate(created_at=F("date_joined")), serialize)
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
            if not data["active"] and user.role == "LAWYER" and Case.objects.filter(lawyer=user).exclude(state__in=[Case.State.CLOSED, Case.State.REJECTED]).exists():
                raise IdentityError("ACTIVE_CASES", "Transfira os casos ativos antes de suspender o profissional.", 409)
            user.is_active = data["active"]
            user.auth_version += 1
            user.save(update_fields=["is_active", "auth_version"])
            audit(request.user, "USER_ACCESS_CHANGED", request.portal, targetId=str(user.pk), active=user.is_active, reason=data["reason"])
        return Response(serialize(user))
