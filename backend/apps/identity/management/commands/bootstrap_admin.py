from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from apps.identity.models import ActionToken, User
from apps.identity.services import audit, issue_token


class Command(BaseCommand):
    help = "Prepara o administrador inicial e envia ativação ao e-mail configurado."

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Administrador")

    def handle(self, *args, **options):
        email = getattr(settings, "IUSTUS_INITIAL_ADMIN_EMAIL", "").strip().lower()
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("Configure IUSTUS_INITIAL_ADMIN_EMAIL com um e-mail válido.") from exc
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [73145001])
            admin = User.objects.select_for_update().filter(role=User.Role.ADMIN).first()
            if admin:
                if admin.email != email or admin.email_verified_at or admin.has_usable_password() or not admin.is_active:
                    raise CommandError("Já existe administrador. Nenhum privilégio foi alterado.")
            else:
                if User.objects.filter(email__iexact=email).exists():
                    raise CommandError("Este e-mail já possui conta. Nenhum privilégio foi alterado.")
                admin = User(email=email, first_name=options["name"], role=User.Role.ADMIN)
                admin.set_unusable_password()
                admin.save()
            ActionToken.objects.filter(user=admin, purpose="INVITE", consumed_at__isnull=True).update(consumed_at=timezone.now())
            issue_token("INVITE", admin.email, "team", user=admin)
            audit(admin, "ADMIN_BOOTSTRAPPED", "team")
        self.stdout.write(self.style.SUCCESS("Ativação enfileirada por e-mail. Defina a senha pelo link e configure MFA para entrar."))
