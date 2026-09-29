import time
from django.core.management.base import BaseCommand
from jobs.communication import deliver_case_email
class Command(BaseCommand):
    help = "Entrega notificações genéricas de casos; settings local grava arquivos."
    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
    def handle(self, *args, **options):
        try:
            while True:
                if not deliver_case_email():
                    if options["once"]:
                        break
                    time.sleep(2)
        except KeyboardInterrupt:
            self.stdout.write("Worker encerrado.")
