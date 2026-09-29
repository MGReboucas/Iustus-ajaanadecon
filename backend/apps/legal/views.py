from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from apps.cases.models import Case
from apps.cases.serializers import VersionInput
from apps.cases.services import changed, get_case, expect_state, expect_version
from apps.cases.views import CaseView
from apps.documents.models import DocumentVersion
from apps.documents.services import version_data
from apps.identity.security import IdentityError
from .models import LegalWork, LegalTask

class WorkflowInput(VersionInput):
    action = serializers.ChoiceField(choices=["START", "SIGN", "VERIFY", "RETURN_MANDATE", "DRAFT", "PUBLISH", "FILE", "UPDATE", "TASK", "RESCHEDULE", "COMPLETE", "CLOSE"])
    text = serializers.CharField(max_length=50000, required=False, default="", allow_blank=True)
    documentId = serializers.UUIDField(required=False)
    position = serializers.ChoiceField(choices=["AUTHOR", "DEFENDANT", "APPLICANT"], required=False)
    processNumber = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    authority = serializers.CharField(max_length=200, required=False, default="", allow_blank=True)
    protocol = serializers.CharField(max_length=200, required=False, default="", allow_blank=True)
    taskId = serializers.UUIDField(required=False)
    kind = serializers.ChoiceField(choices=LegalTask._meta.get_field("kind").choices, required=False)
    title = serializers.CharField(max_length=200, required=False)
    dueAt = serializers.DateTimeField(required=False)
    confirmed = serializers.BooleanField(required=False, default=False)


def require(condition, message):
    if not condition:
        raise IdentityError("WORKFLOW_REQUIREMENT", message, 422)


def document(item, data, uploader=None):
    query = DocumentVersion.objects.filter(pk=data.get("documentId"), document__case=item,
                                          status=DocumentVersion.Status.AVAILABLE)
    if uploader:
        query = query.filter(uploaded_by=uploader)
    result = query.first()
    require(result is not None, "Selecione um documento verificado deste caso, enviado pelo responsável pela ação.")
    return result


def workflow_data(item, user):
    work = LegalWork.objects.filter(case=item).select_related("mandate", "signed_mandate", "receipt").first()
    data = {"version": item.version, "state": item.state, "scope": "", "position": "", "processNumber": "",
            "authority": "", "publishedText": "", "protocol": "", "mandate": None, "signedMandate": None, "receipt": None}
    if work:
        data.update(scope=work.scope, position=work.client_position, processNumber=work.process_number,
                    authority=work.authority, publishedText=work.published_text, protocol=work.protocol,
                    mandate=version_data(work.mandate) if work.mandate else None,
                    signedMandate=version_data(work.signed_mandate) if work.signed_mandate else None,
                    receipt=version_data(work.receipt) if work.receipt else None)
        if user.role == "LAWYER":
            data["draft"] = work.draft
    data["tasks"] = [{"id": str(task.pk), "kind": task.kind, "title": task.title,
                      "dueAt": task.due_at.isoformat(), "completedAt": task.completed_at.isoformat() if task.completed_at else None,
                      "outcome": task.outcome} for task in item.legal_tasks.order_by("due_at", "id")]
    return data


class WorkflowView(CaseView):
    def get(self, request, case_id):
        return Response(workflow_data(get_case(request.user, case_id), request.user))

    def post(self, request, case_id):
        self.limited(request)
        data = self.data(request, WorkflowInput)
        action = data["action"]
        self.role(request, "CLIENT" if action == "SIGN" else "LAWYER")
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            expect_version(item, data["version"])
            expect_state(item, Case.State.ACCEPTED, Case.State.MANDATE, Case.State.PREPARING, Case.State.TRACKING)
            work, _ = LegalWork.objects.get_or_create(case=item)
            reason, public = data["text"], True
            if action == "START":
                expect_state(item, Case.State.ACCEPTED)
                require(len(data["text"].strip()) >= 10 and data.get("position"), "Descreva as etapas contratadas e a posição do cliente.")
                work.scope, work.client_position = data["text"], data["position"]
                work.authority, work.process_number = data["authority"], data["processNumber"]
                work.mandate = document(item, data, request.user)
                item.state = Case.State.MANDATE
            elif action == "SIGN":
                expect_state(item, Case.State.MANDATE)
                work.signed_mandate = document(item, data, request.user)
                reason = "Cliente enviou procuração para conferência."
            elif action == "RETURN_MANDATE":
                expect_state(item, Case.State.MANDATE)
                require(work.signed_mandate and len(data["text"].strip()) >= 5, "Informe o ajuste necessário na procuração devolvida.")
                work.signed_mandate = None
            elif action == "VERIFY":
                expect_state(item, Case.State.MANDATE)
                require(work.signed_mandate and work.signed_mandate.status == "AVAILABLE" and data["confirmed"], "Confira a procuração devolvida antes de continuar.")
                item.state = Case.State.PREPARING
                reason = "Procuração conferida pelo advogado responsável."
            elif action == "DRAFT":
                expect_state(item, Case.State.PREPARING, Case.State.TRACKING)
                require(len(data["text"].strip()) >= 10, "Preencha a minuta da peça.")
                work.draft = data["text"]
                reason, public = "Minuta interna atualizada.", False
            elif action == "PUBLISH":
                expect_state(item, Case.State.PREPARING, Case.State.TRACKING)
                require(work.draft and data["confirmed"], "Revise a minuta e confirme a publicação ao cliente.")
                work.published_text, work.published_at = work.draft, timezone.now()
                reason = "Peça revisada e disponibilizada ao cliente."
            elif action == "FILE":
                expect_state(item, Case.State.PREPARING, Case.State.TRACKING)
                require(work.published_text and data["protocol"] and data["authority"] and data["confirmed"], "Informe órgão, protocolo e confirme o protocolo externo da peça publicada.")
                work.receipt = document(item, data, request.user)
                work.protocol, work.authority, work.process_number = data["protocol"], data["authority"], data["processNumber"]
                item.state = Case.State.TRACKING
                reason = "Protocolo registrado: " + work.protocol
            elif action in ("TASK", "RESCHEDULE"):
                require(data.get("dueAt") and len(data["text"].strip()) >= 5, "Informe a data e o motivo da inclusão ou remarcação.")
                if action == "TASK":
                    require(data.get("kind") and data.get("title"), "Informe tipo e título do compromisso.")
                    LegalTask.objects.create(case=item, kind=data["kind"], title=data["title"], due_at=data["dueAt"])
                else:
                    task = item.legal_tasks.filter(pk=data.get("taskId"), completed_at__isnull=True).first()
                    if not task:
                        raise Http404
                    reason = f"{task.title}: data alterada de {task.due_at.isoformat()} para {data['dueAt'].isoformat()}. " + data["text"]
                    task.due_at = data["dueAt"]
                    task.save()
            elif action == "COMPLETE":
                require(len(data["text"].strip()) >= 5, "Registre o resultado do compromisso.")
                task = item.legal_tasks.filter(pk=data.get("taskId"), completed_at__isnull=True).first()
                if not task:
                    raise Http404
                task.completed_at, task.outcome = timezone.now(), data["text"]
                task.save()
                reason = task.title + ": " + data["text"]
            elif action == "UPDATE":
                require(len(data["text"].strip()) >= 5, "Descreva a movimentação para o cliente.")
            elif action == "CLOSE":
                expect_state(item, Case.State.PREPARING, Case.State.TRACKING)
                require(data["confirmed"] and len(data["text"].strip()) >= 10, "Confirme a revisão das pendências e descreva o resultado do atendimento.")
                require(not item.legal_tasks.filter(completed_at__isnull=True).exists()
                        and not item.information_requests.filter(resolved_at__isnull=True).exists(),
                        "Conclua os prazos, audiências, etapas e complementos antes de encerrar.")
                item.state = Case.State.CLOSED
            work.save()
            changed(item, request.user, "LEGAL_" + action, reason, public=public,
                    snapshot={"text": work.draft if action == "DRAFT" else work.published_text if action == "PUBLISH" else "",
                              "documentId": str(data.get("documentId", "")), "protocol": work.protocol,
                              "authority": work.authority, "processNumber": work.process_number,
                              "taskId": str(data.get("taskId", ""))})
        return Response(workflow_data(item, request.user))
