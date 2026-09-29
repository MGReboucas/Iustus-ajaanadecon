import time
from django.conf import settings
from django.db import close_old_connections
from jobs.documents import scan_one
from django.core.management import call_command
from django.core.management.base import BaseCommand
from jobs.mail import deliver_one
from jobs.communication import deliver_case_email, schedule_reminders
class Command(BaseCommand):
    help = "Executa e-mails, lembretes, scanner e limpeza de exportações; --once executa um ciclo limitado."
    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                schedule_reminders()
                for _ in range(100):
                    identity = deliver_one()
                    case = deliver_case_email()
                    if not identity and not case: break
                call_command("purge_case_exports", verbosity=0)
                # Um documento por ciclo mantém espaço para processar e-mails.
                if settings.DOCUMENT_STORAGE_BACKEND == "s3" or settings.DOCUMENT_LOCAL_STORAGE_ENABLED:
                    scan_one()
                close_old_connections()
                if options["once"]: break
                time.sleep(30)
        except KeyboardInterrupt:
            self.stdout.write("Worker encerrado.")
