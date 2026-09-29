from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.utils import timezone
from rest_framework.response import Response

from apps.cases.models import Case, CaseEvent, InformationRequest
from apps.cases.services import accessible, case_data, get_case, submission_access
from apps.cases.views import CaseView
from apps.legal.models import LegalTask
from apps.identity.security import IdentityError
from apps.identity.services import audit
from .models import Message, Notification
from .serializers import MessageInput, ReadInput
from .services import message_data, notification_data, visible_notifications, create_notice


class MessagesView(CaseView):
    def get(self, request, case_id):
        item = get_case(request.user, case_id)
        query = item.messages.select_related("author")
        if request.user.role == "CLIENT":
            query = query.filter(visibility=Message.Visibility.PUBLIC)
        return self.listed(request, query, message_data)

    def post(self, request, case_id):
        self.role(request, "CLIENT", "LAWYER")
        self.limited(request)
        data = self.data(request, MessageInput)
        if data["visibility"] == Message.Visibility.INTERNAL and request.user.role != "LAWYER":
            raise IdentityError("FORBIDDEN", "Notas internas são restritas ao advogado responsável.", 403)
        with transaction.atomic():
            item = get_case(request.user, case_id, locked=True)
            previous = item.messages.filter(author=request.user, client_id=data["clientMessageId"]).first()
            if previous:
                if previous.text != data["text"] or previous.visibility != data["visibility"]:
                    raise IdentityError("IDEMPOTENCY_CONFLICT", "Esta chave já foi usada para outra mensagem.", 409)
                return Response(message_data(previous))
            if item.state in (Case.State.DRAFT, Case.State.REJECTED, Case.State.CLOSED) or not item.lawyer_id:
                raise IdentityError("CONVERSATION_UNAVAILABLE", "A conversa fica disponível após a atribuição de um advogado, enquanto o caso está em atendimento.", 409)
            message = Message.objects.create(case=item, author=request.user, text=data["text"],
                visibility=data["visibility"], client_id=data["clientMessageId"])
            audit(request.user, "case.message_created", request.portal, caseId=str(item.pk), messageId=str(message.pk), visibility=message.visibility)
            if message.visibility == Message.Visibility.PUBLIC:
                recipient_id = item.lawyer_id if request.user.role == "CLIENT" else item.owner_id
                create_notice(recipient_id=recipient_id, case=item, source_key=f"message:{message.pk}",
                    kind="MESSAGE", title="Você recebeu uma mensagem no caso")
        return Response(message_data(message), status=201)


class NotificationsView(CaseView):
    def get(self, request):
        query = visible_notifications(request.user)
        unread = request.query_params.get("unread", "false")
        if unread not in ("true", "false"):
            raise IdentityError("INVALID_INPUT", "Filtro de leitura inválido.")
        if unread == "true":
            query = query.filter(read_at__isnull=True)
        return self.listed(request, query, notification_data)


class NotificationReadView(CaseView):
    def post(self, request, notification_id):
        self.data(request, ReadInput)
        self.limited(request)
        with transaction.atomic():
            item = visible_notifications(request.user).select_for_update().filter(pk=notification_id).first()
            if not item:
                raise Http404
            if item.read_at is None:
                item.read_at = timezone.now()
                item.save(update_fields=["read_at"])
        return Response(notification_data(item))


class OverviewView(CaseView):
    def get(self, request):
        user = request.user
        admin = user.role == "ADMIN"
        cases = accessible(user, administrative=admin)
        counts = dict(cases.values("state").annotate(total=Count("id")).values_list("state", "total"))
        pending = InformationRequest.objects.filter(case__in=cases, resolved_at__isnull=True)
        if user.role == "CLIENT":
            pending = pending.filter(responded_at__isnull=True)
        else:
            pending = pending.filter(responded_at__isnull=False)
        if admin:
            attention = cases.filter(lawyer__isnull=True).exclude(state=Case.State.REJECTED)
        elif user.role == "CLIENT":
            attention = cases.filter(Q(state=Case.State.DRAFT) | Q(state=Case.State.MANDATE, legal_work__signed_mandate__isnull=True) | Q(pk__in=pending.values("case_id")))
        else:
            attention = cases.filter(Q(state__in=[Case.State.SUBMITTED, Case.State.TRIAGE, Case.State.ACCEPTED, Case.State.PREPARING]) | Q(state=Case.State.MANDATE, legal_work__signed_mandate__isnull=False) | Q(pk__in=LegalTask.objects.filter(completed_at__isnull=True, due_at__lte=timezone.now()).values("case_id")) | Q(pk__in=pending.values("case_id")))
        events = CaseEvent.objects.filter(case__in=cases, public=True).exclude(action__in=["DRAFT_CREATED", "DRAFT_UPDATED"]).select_related("case").order_by("-created_at", "-id")
        return Response({
            "totalCases": sum(counts.values()), "attentionCount": attention.count(),
            "unreadCount": visible_notifications(user).filter(read_at__isnull=True).count(),
            "states": [{"id": state, "label": label, "count": counts.get(state, 0)} for state, label in Case.State.choices],
            "attentionCases": [case_data(item, administrative=admin) for item in attention.order_by("updated_at", "id")[:5]],
            "recentActivity": [] if admin else [{"id": str(event.pk), "caseId": str(event.case_id),
                "reference": str(event.case_id)[:8].upper(), "title": event.case.title,
                "action": event.action, "stateLabel": event.case.get_state_display(), "createdAt": event.created_at.isoformat()}
                for event in events[:5]],
            "submission": submission_access(user) if user.role == "CLIENT" else None,
        })
