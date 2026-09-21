import time

from django.core.management.base import BaseCommand

from apps.documents.models import DocumentVersion
from django.utils import timezone
from jobs.documents import scan_one


class Command(BaseCommand):
    help = "Verifica documentos em quarentena pelo ClamAV. Falhas nunca liberam download."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--retry-failed", action="store_true", help="Reagenda versões com erro após corrigir o scanner.")

    def handle(self, *args, **options):
        if options["retry_failed"]:
            DocumentVersion.objects.filter(status="ERROR").update(attempts=0, available_at=timezone.now())
        try:
            while True:
                if not scan_one():
                    if options["once"]:
                        break
                    time.sleep(2)
        except KeyboardInterrupt:
            self.stdout.write("Worker encerrado.")
