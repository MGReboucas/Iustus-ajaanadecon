from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from apps.cases.serializers import VersionInput
from apps.cases.services import get_case
from apps.cases.views import CaseView
from .proposals import publish_proposal, decide_proposal, proposal_list


class ProposalInput(VersionInput):
    scope = serializers.CharField(max_length=50000)
    feeCents = serializers.IntegerField(min_value=0, max_value=99999999999)
    expenses = serializers.CharField(max_length=50000)
    paymentTerms = serializers.CharField(max_length=50000)
    validUntil = serializers.DateTimeField()


class DecisionInput(VersionInput):
    accepted = serializers.BooleanField()


def proposal_data(item):
    return {"id": str(item.pk), "number": item.number, "scope": item.scope,
            "feeCents": item.fee_cents, "currency": "BRL", "expenses": item.expenses,
            "paymentTerms": item.payment_terms, "validUntil": item.valid_until.isoformat(),
            "status": item.status, "authorId": str(item.author_id),
            "decidedById": str(item.decided_by_id) if item.decided_by_id else None,
            "decidedAt": item.decided_at.isoformat() if item.decided_at else None,
            "createdAt": item.created_at.isoformat()}


class ProposalsView(CaseView):
    def get(self, request, case_id):
        return self.listed(request, proposal_list(request.user, case_id), proposal_data)

    @transaction.atomic
    def post(self, request, case_id):
        self.limited(request)
        data = self.data(request, ProposalInput)
        proposal = publish_proposal(request.user, case_id, data["version"], scope=data["scope"],
            fee_cents=data["feeCents"], expenses=data["expenses"], payment_terms=data["paymentTerms"],
            valid_until=data["validUntil"])
        return Response({"proposal": proposal_data(proposal),
                         "version": get_case(request.user, case_id).version}, status=201)


class ProposalDecisionView(CaseView):
    @transaction.atomic
    def post(self, request, case_id, proposal_id):
        self.limited(request)
        data = self.data(request, DecisionInput)
        proposal = decide_proposal(request.user, case_id, proposal_id, data["version"], accepted=data["accepted"])
        return Response({"proposal": proposal_data(proposal),
                         "version": get_case(request.user, case_id).version})
