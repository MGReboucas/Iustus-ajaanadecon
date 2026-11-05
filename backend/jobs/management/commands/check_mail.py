from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.identity.models import IdentityEmail
from apps.communication.models import CaseEmail
from jobs.branded_mail import build_message


class Command(BaseCommand):
    help = "Show aggregate queue health; optionally verify SMTP or send an explicitly addressed test."

    def add_arguments(self, parser):
        parser.add_argument("--connect", action="store_true")
        parser.add_argument("--send-to")

    def handle(self, *args, **options):
        for name, query in (("identity", IdentityEmail.objects.filter(sent_at__isnull=True)),
                            ("case", CaseEmail.objects.filter(sent_at__isnull=True, cancelled_at__isnull=True))):
            self.stdout.write(f"{name}: pending={query.count()} exhausted={query.filter(attempts__gte=5).count()}")
        try:
            if options["send_to"]:
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
