"""Versioned proposals. No collection or automatic start of legal work."""
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.utils import timezone
from apps.cases.models import Case
from apps.cases.services import get_case, expect_version, expect_state, changed
from apps.identity.models import User
from apps.identity.security import IdentityError
from .models import ServiceProposal


def proposal_list(user, case_id):
    case = get_case(user, case_id)
    return case.service_proposals.order_by("-number")


@transaction.atomic
def publish_proposal(user, case_id, version, *, scope, fee_cents, expenses, payment_terms, valid_until):
    case = get_case(user, case_id, locked=True)
    if user.role != User.Role.LAWYER:
        raise IdentityError("PROPOSAL_FORBIDDEN", "Somente o advogado pode apresentar proposta.", 403)
    expect_version(case, version)
    expect_state(case, Case.State.SUBMITTED, Case.State.TRIAGE, Case.State.WAITING, Case.State.ACCEPTED,
                 Case.State.MANDATE, Case.State.PREPARING, Case.State.TRACKING)
    fields = (scope, expenses, payment_terms)
    if any(not isinstance(value, str) or not value.strip() or len(value) > 50000 for value in fields):
        raise IdentityError("INVALID_PROPOSAL", "Informe escopo, despesas e pagamento.", 422)
    if isinstance(fee_cents, bool) or not isinstance(fee_cents, int) or not 0 <= fee_cents <= 99999999999:
        raise IdentityError("INVALID_PROPOSAL", "Honorarios invalidos.", 422)
    if timezone.is_naive(valid_until) or valid_until <= timezone.now():
        raise IdentityError("INVALID_PROPOSAL", "A validade deve ser futura.", 422)
    number = (case.service_proposals.aggregate(value=Max("number"))["value"] or 0) + 1
    case.service_proposals.filter(status=ServiceProposal.Status.OPEN).update(status=ServiceProposal.Status.SUPERSEDED)
    proposal = ServiceProposal.objects.create(case=case, number=number, author=user, scope=scope.strip(),
        fee_cents=fee_cents, expenses=expenses.strip(), payment_terms=payment_terms.strip(), valid_until=valid_until)
    changed(case, user, "PROPOSAL_PUBLISHED", proposalId=str(proposal.pk), number=number)
    return proposal


@transaction.atomic
def decide_proposal(user, case_id, proposal_id, version, *, accepted):
    case = get_case(user, case_id, locked=True)
    if user.role != User.Role.CLIENT:
        raise IdentityError("PROPOSAL_FORBIDDEN", "Somente o titular pode decidir a proposta.", 403)
    proposal = case.service_proposals.filter(pk=proposal_id).first()
    if not proposal:
        raise Http404
    if not isinstance(accepted, bool):
        raise IdentityError("INVALID_PROPOSAL", "Informe aceite ou recusa.", 422)
    target = ServiceProposal.Status.ACCEPTED if accepted else ServiceProposal.Status.DECLINED
    # Lost response: repeating the same decision does not create another event.
    if proposal.status == target and proposal.decided_by_id == user.pk:
        return proposal
    expect_version(case, version)
    expect_state(case, Case.State.SUBMITTED, Case.State.TRIAGE, Case.State.WAITING, Case.State.ACCEPTED,
                 Case.State.MANDATE, Case.State.PREPARING, Case.State.TRACKING)
    if proposal.status != ServiceProposal.Status.OPEN or proposal.valid_until <= timezone.now():
        raise IdentityError("PROPOSAL_UNAVAILABLE", "Proposta encerrada ou expirada.", 409)
    proposal.status, proposal.decided_by, proposal.decided_at = target, user, timezone.now()
    proposal.save(update_fields=["status", "decided_by", "decided_at"])
    changed(case, user, "PROPOSAL_" + target, proposalId=str(proposal.pk), number=proposal.number)
    return proposal
