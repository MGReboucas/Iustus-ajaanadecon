from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from apps.cases.views import CaseView
from apps.identity.serializers import StrictSerializer
from apps.identity.security import IdentityError
from apps.identity.services import audit
from .models import PrivacyRequest
class Input(StrictSerializer):
    kind = serializers.ChoiceField(choices=["ACCESS", "CORRECTION", "DELETION", "OTHER"])
    description = serializers.CharField(min_length=10, max_length=4000)
class Resolution(StrictSerializer):
    response = serializers.CharField(min_length=10, max_length=4000)
def serialize(item):
    return {"id": str(item.pk), "ownerEmail": item.owner.email, "kind": item.kind, "description": item.description,
            "status": item.status, "response": item.response, "createdAt": item.created_at.isoformat()}
class RequestsView(CaseView):
    def get(self, request):
        query = PrivacyRequest.objects.select_related("owner")
        if request.user.role != "ADMIN": query = query.filter(owner=request.user)
        return self.listed(request, query, serialize)
    def post(self, request):
        self.limited(request)
        data = self.data(request, Input)
        with transaction.atomic():
            item = PrivacyRequest.objects.create(owner=request.user, **data)
            audit(request.user, "PRIVACY_REQUESTED", request.portal, requestId=str(item.pk))
        return Response(serialize(item), status=201)
class ResolveView(CaseView):
    def post(self, request, pk):
        self.role(request, "ADMIN")
        self.limited(request)
        data = self.data(request, Resolution)
        with transaction.atomic():
            item = PrivacyRequest.objects.select_for_update().filter(pk=pk).first()
            if not item: raise Http404
            if item.status != "OPEN": raise IdentityError("CONFLICT", "Solicitação já respondida.", 409)
            item.status, item.response = "ANSWERED", data["response"]
            item.resolved_at, item.resolved_by = timezone.now(), request.user
            item.save()
            audit(request.user, "PRIVACY_ANSWERED", request.portal, requestId=str(item.pk))
        return Response(serialize(item))
