import time
from django.core.management import call_command
from django.core.management.base import BaseCommand
from jobs.mail import deliver_one
from jobs.communication import deliver_case_email, schedule_reminders
class Command(BaseCommand):
    help = "Executa e-mails, lembretes e limpeza de exportações; --once executa um ciclo limitado."
    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
    def handle(self, *args, **options):
        try:
            while True:
                schedule_reminders()
                for _ in range(100):
                    identity = deliver_one()
                    case = deliver_case_email()
                    if not identity and not case: break
                call_command("purge_case_exports", verbosity=0)
                if options["once"]: break
                time.sleep(30)
        except KeyboardInterrupt:
            self.stdout.write("Worker encerrado.")
