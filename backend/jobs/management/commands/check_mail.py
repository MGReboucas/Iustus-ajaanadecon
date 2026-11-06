from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.identity.models import IdentityEmail, MailWorkerHeartbeat
from django.utils import timezone
from datetime import timedelta
from apps.communication.models import CaseEmail
from jobs.branded_mail import build_message


class Command(BaseCommand):
    help = "Show aggregate queue health; optionally verify SMTP or send an explicitly addressed test."

    def add_arguments(self, parser):
        parser.add_argument("--connect", action="store_true")
        parser.add_argument("--send-to")
        parser.add_argument("--queue-test-to", help="Queue a harmless test through the real worker instead of sending directly.")
        parser.add_argument("--strict", action="store_true", help="Fail for stopped worker, delayed or exhausted mail.")

    def handle(self, *args, **options):
        if options["send_to"] and options["queue_test_to"]:
            raise CommandError("Choose direct SMTP test or queued test, not both.")
        unhealthy = False
        for name, query in (("identity", IdentityEmail.objects.filter(sent_at__isnull=True, cancelled_at__isnull=True)),
                            ("case", CaseEmail.objects.filter(sent_at__isnull=True, cancelled_at__isnull=True))):
            self.stdout.write(f"{name}: pending={query.count()} exhausted={query.filter(attempts__gte=5).count()}")
            unhealthy |= query.filter(attempts__gte=5).exists() or query.filter(available_at__lt=timezone.now() - timedelta(minutes=15)).exists()
        alive = MailWorkerHeartbeat.objects.filter(updated_at__gte=timezone.now() - timedelta(minutes=5)).exists()
        self.stdout.write("worker: " + ("active" if alive else "heartbeat missing or stale"))
        try:
            if options["queue_test_to"]:
                from apps.identity.security import encrypt
                validate_email(options["queue_test_to"])
                item = IdentityEmail.objects.create(recipient=options["queue_test_to"],
                    subject="Iustus: teste da fila de emails",
                    encrypted_body=encrypt("Este é um teste autorizado do envio da Iustus. A mensagem passou pela fila persistente e pelo worker de envio.\n\nNão é uma cobrança nem altera sua conta. Confira se o logo, o texto e o botão aparecem corretamente.\n\n" + settings.PORTAL_ORIGINS["client"] + "/acessar"),
                    available_at=timezone.now(), context={"kind": "OPERATOR_TEST"})
                self.stdout.write(f"Queued test id={item.pk}. Confirm worker acceptance and inbox arrival separately.")
            elif options["send_to"]:
                validate_email(options["send_to"])
                if build_message("Iustus: teste de envio", "A conexão de e-mail da Iustus está funcionando.\n\n" +
                        settings.PORTAL_ORIGINS["client"] + "/acessar", [options["send_to"]]).send() != 1:
                    raise CommandError("The mail server did not accept the message.")
                self.stdout.write("Test accepted by mail server. Confirm arrival in the recipient mailbox.")
            elif options["connect"]:
                with get_connection() as connection:
                    if not connection.connection:
                        raise CommandError("SMTP connection unavailable.")
                self.stdout.write("SMTP connection/authentication succeeded. No email sent.")
        except ValidationError:
            raise CommandError("Invalid test recipient.") from None
        except Exception as exc:
            raise CommandError("Mail check failed: " + type(exc).__name__) from None
        if options["strict"] and (unhealthy or not alive):
            raise CommandError("Mail queue requires operator attention.")
