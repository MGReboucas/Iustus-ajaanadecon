from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.legal.models import CaseExport
from integrations.storage.private import object_path

class Command(BaseCommand):
    help = "Remove pacotes expirados; mantém metadados para auditoria. Executar periodicamente."

    def handle(self, *args, **options):
        count = 0
        while True:
            with transaction.atomic():
                row = CaseExport.objects.select_for_update().filter(expires_at__lte=timezone.now(), purged_at__isnull=True).first()
                if not row:
                    break
                object_path(row.object_key).unlink(missing_ok=True)
                row.purged_at = timezone.now()
                row.save(update_fields=["purged_at"])
                count += 1
        self.stdout.write(f"Pacotes expirados removidos: {count}")
