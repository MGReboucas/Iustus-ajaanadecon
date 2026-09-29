import re

from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.utils import timezone
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from apps.identity.models import User
from apps.identity.security import IdentityError, digest, throttle
from apps.identity.views import IdentityView
from apps.documents.models import DocumentVersion, RequestAttachment
from apps.documents.services import version_data
from . import serializers as inputs
from .models import Case, InformationRequest
from .services import (accessible, case_data, changed, edit_draft, expect_state, expect_version,
                       get_case, record, submission_access)


class Page(CursorPagination):
    page_size = 20
    ordering = ("-created_at", "-id")


class CaseView(IdentityView):
    def role(self, request, *roles):
        if request.user.role not in roles:
            raise IdentityError("FORBIDDEN", "Ação não permitida para este perfil.", 403)

    def limited(self, request):
        throttle("case-write", str(request.user.pk), 60)

    def listed(self, request, query, serialize):
        page = Page()
        rows = page.paginate_queryset(query, request, view=self)
        # Somente cursor, sem vazar URL interna/esquema do proxy.
        from urllib.parse import parse_qs, urlsplit
        url = page.get_next_link()
        cursor = parse_qs(urlsplit(url).query).get("cursor", [None])[0] if url else None
        return Response({"results": [serialize(row) for row in rows], "nextCursor": cursor})


class CatalogView(CaseView):
    def get(self, request):
        return Response({"categories": [{"id": key, "label": label} for key, label in Case.Category.choices],
                         "states": [{"id": key, "label": label} for key, label in Case.State.choices],
                         "submission": submission_access(request.user) if request.user.role == "CLIENT" else None})


class CasesView(CaseView):
    def get(self, request):
        admin = request.user.role == "ADMIN"
        query = accessible(request.user, administrative=admin)
        state = request.query_params.get("state")
        if state:
            if state not in Case.State.values:
                raise IdentityError("INVALID_INPUT", "Estado desconhecido.")
            query = query.filter(state=state)
        return self.listed(request, query, lambda item: case_data(item, administrative=admin))

    def post(self, request):
        self.role(request, "CLIENT")
        self.limited(request)
        data = self.data(request, inputs.DraftInput)
        with transaction.atomic():
            item = Case(owner=request.user)
            edit_draft(item, data)
            item.save()
            record(item, request.user, "DRAFT_CREATED")
        return Response(case_data(item, detail=True), status=201)


class SummaryView(CaseView):
    def get(self, request, case_id):
        self.role(request, "ADMIN")
        return Response(case_data(get_case(request.user, case_id, administrative=True), administrative=True))


class DetailView(CaseView):
    def get(self, request, case_id):
        return Response(case_data(get_case(request.user, case_id), detail=True))

    def patch(self, request, case_id):
        self.role(request, "CLIENT")
        self.limited(request)
        data = self.data(request, inputs.EditInput)
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            expect_version(item, data["version"])
            expect_state(item, Case.State.DRAFT)
            edit_draft(item, data)
            changed(item, request.user, "DRAFT_UPDATED")
        return Response(case_data(item, detail=True))


class SubmitView(CaseView):
    def post(self, request, case_id):
        self.role(request, "CLIENT")
        self.limited(request)
        data = self.data(request, inputs.VersionInput)
        key = request.headers.get("Idempotency-Key", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", key):
            raise IdentityError("IDEMPOTENCY_REQUIRED", "Envie uma chave válida para esta submissão.")
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            if item.submission_key == digest(key):
                if item.submission_version != data["version"]:
                    raise IdentityError("IDEMPOTENCY_CONFLICT", "A chave foi usada em outra versão.", 409)
                return Response(case_data(item, detail=True))
            expect_version(item, data["version"])
            expect_state(item, Case.State.DRAFT)
            if not item.title.strip() or len(item.description.strip()) < 20 or not item.category or not item.scope_acknowledged:
                raise IdentityError("INCOMPLETE_CASE", "Preencha título, categoria, relato de pelo menos 20 caracteres e ciência do escopo.", 422)
            if not submission_access(request.user)["canSubmit"]:
                raise IdentityError("SUBMISSION_UNAVAILABLE", "Envio indisponível. A assinatura ainda não está integrada; mantenha o rascunho.", 422)
            item.state = Case.State.SUBMITTED
            item.submitted_at = timezone.now()
            item.submission_key, item.submission_version = digest(key), item.version
            changed(item, request.user, "SUBMITTED")
        return Response(case_data(item, detail=True))


class LawyersView(CaseView):
    def get(self, request):
        self.role(request, "ADMIN")
        query = User.objects.filter(role="LAWYER", is_active=True, email_verified_at__isnull=False,
                                    mfadevice__confirmed_at__isnull=False)
        return self.listed(request, query.annotate(created_at=F("date_joined")),
                           lambda user: {"id": str(user.pk), "name": user.first_name, "email": user.email})


class AssignmentView(CaseView):
    def post(self, request, case_id):
        self.role(request, "ADMIN")
        self.limited(request)
        data = self.data(request, inputs.AssignmentInput)
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True, administrative=True)
            expect_version(item, data["version"])
            expect_state(item, Case.State.SUBMITTED, Case.State.TRIAGE, Case.State.WAITING, Case.State.ACCEPTED)
            lawyer = User.objects.select_for_update().filter(pk=data["lawyerId"], role="LAWYER", is_active=True,
                email_verified_at__isnull=False, mfadevice__confirmed_at__isnull=False).first()
            if not lawyer:
                raise IdentityError("INVALID_LAWYER", "Selecione um advogado ativo com MFA confirmado.")
            if item.lawyer_id == lawyer.pk:
                raise IdentityError("ALREADY_ASSIGNED", "Este advogado já é o responsável.", 409)
            previous = str(item.lawyer_id) if item.lawyer_id else None
            item.lawyer = lawyer
            changed(item, request.user, "ASSIGNED", data["reason"], public=False, previousLawyer=previous, lawyerId=str(lawyer.pk))
        return Response(case_data(item, administrative=True))


class TransitionView(CaseView):
    def post(self, request, case_id):
        self.role(request, "LAWYER")
        self.limited(request)
        data = self.data(request, inputs.TransitionInput)
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            expect_version(item, data["version"])
            target = data["targetState"]
            if target == Case.State.TRIAGE:
                expect_state(item, Case.State.SUBMITTED)
            else:
                expect_state(item, Case.State.TRIAGE)
                if not data["reason"]:
                    raise IdentityError("REASON_REQUIRED", "Informe uma justificativa visível ao cliente.", 422)
                if target == Case.State.ACCEPTED and not all(data[field] for field in ("scopeConfirmed", "conflictChecked", "informationSufficient")):
                    raise IdentityError("CHECKLIST_REQUIRED", "Confirme escopo, análise de conflito e suficiência das informações.", 422)
            item.state = target
            changed(item, request.user, "TRIAGE_DECISION" if target != Case.State.TRIAGE else "TRIAGE_STARTED", data["reason"],
                    checklist={field: data[field] for field in ("scopeConfirmed", "conflictChecked", "informationSufficient")})
        return Response(case_data(item, detail=True))


class RequestsView(CaseView):
    def get(self, request, case_id):
        item = get_case(request.user, case_id)
        return self.listed(request, item.information_requests.prefetch_related("attachments__version"), lambda row: {
            "id": str(row.pk), "description": row.description, "response": row.response, "resolution": row.resolution,
            "resolved": row.resolved_at is not None, "responded": row.responded_at is not None,
            "attachments": [version_data(link.version) for link in row.attachments.all()]})

    def post(self, request, case_id):
        self.role(request, "LAWYER")
        self.limited(request)
        data = self.data(request, inputs.RequestInput)
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            expect_version(item, data["version"])
            expect_state(item, Case.State.TRIAGE)
            pending = InformationRequest.objects.create(case=item, author=request.user, description=data["description"])
            item.state = Case.State.WAITING
            changed(item, request.user, "INFORMATION_REQUESTED", data["description"], requestId=str(pending.pk))
        return Response(case_data(item, detail=True), status=201)


class RequestActionView(CaseView):
    def post(self, request, case_id, request_id, action):
        self.role(request, "CLIENT" if action == "response" else "LAWYER")
        self.limited(request)
        data = self.data(request, inputs.ResponseInput if action == "response" else inputs.ResolutionInput)
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            expect_version(item, data["version"])
            expect_state(item, Case.State.WAITING)
            pending = item.information_requests.filter(pk=request_id, resolved_at__isnull=True).first()
            if not pending:
                raise Http404
            if action == "response":
                if pending.responded_at:
                    raise IdentityError("ALREADY_RESPONDED", "Esta pendência já recebeu resposta.", 409)
                ids = data["documentVersionIds"]
                versions = list(DocumentVersion.objects.filter(pk__in=ids, document__case=item,
                    uploaded_by=request.user, status=DocumentVersion.Status.AVAILABLE))
                if len(versions) != len(ids):
                    raise IdentityError("INVALID_ATTACHMENT", "Selecione versões próprias, verificadas e pertencentes a este caso.", 422)
                RequestAttachment.objects.bulk_create([RequestAttachment(request=pending, version=version) for version in versions])
                pending.response, pending.responded_at = data["text"], timezone.now()
                event, reason = "INFORMATION_RESPONDED", "Cliente enviou complemento."
            else:
                if not pending.responded_at:
                    raise IdentityError("RESPONSE_REQUIRED", "Aguarde o complemento do cliente.", 422)
                pending.resolution, pending.resolved_at = data["reason"], timezone.now()
                item.state = Case.State.TRIAGE
                event, reason = "INFORMATION_RESOLVED", data["reason"]
            pending.save()
            changed(item, request.user, event, reason, requestId=str(pending.pk))
        return Response(case_data(item, detail=True))


class TimelineView(CaseView):
    def get(self, request, case_id):
        item = get_case(request.user, case_id)
        query = item.events.all()
        if request.user.role == "CLIENT":
            query = query.filter(public=True)
        return self.listed(request, query, lambda event: {"id": str(event.pk), "action": event.action,
            "state": event.state, "reason": event.reason, "createdAt": event.created_at.isoformat()})
