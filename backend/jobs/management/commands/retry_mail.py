from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.identity.models import IdentityEmail
from apps.communication.models import CaseEmail


class Command(BaseCommand):
    help = "Requeue one exhausted message; delivery checks still apply. Does not send mail."

    def add_arguments(self, parser):
        parser.add_argument("queue", choices=("identity", "case"))
        parser.add_argument("id")

    @transaction.atomic
    def handle(self, *args, **options):
        model = IdentityEmail if options["queue"] == "identity" else CaseEmail
        item = model.objects.select_for_update().filter(pk=options["id"], sent_at__isnull=True,
            cancelled_at__isnull=True, attempts__gte=5).first()
        if not item or (item.lease_until and item.lease_until > timezone.now()):
            raise CommandError("Message is not exhausted or is currently leased.")
        item.attempts = 0
        item.available_at = timezone.now()
        item.lease_id = item.lease_until = None
        item.last_error = ""
        item.save(update_fields=["attempts", "available_at", "lease_id", "lease_until", "last_error"])
        self.stdout.write("Message requeued; current permissions and token validity will be checked before sending.")
