import base64
from pathlib import Path

from django.core.management.base import BaseCommand

from jobs.branded_mail import ROOT, render_email


class Command(BaseCommand):
    help = "Generate static HTML previews with synthetic links, without sending mail."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        from django.conf import settings
        output = Path(options["output"])
        output.mkdir(parents=True, exist_ok=True)
        origin = settings.PORTAL_ORIGINS["client"]
        samples = {
            "pagamento": ("Pagamento confirmado: conclua seu cadastro na Iustus", "Seu pagamento foi confirmado. Falta só definir sua senha para acessar a plataforma.\n\n" + origin + "/acessar#member=exemplo-sem-validade\n\nEste link expira em 24 horas. Se não reconhece a solicitação, ignore esta mensagem."),
            "senha": ("Redefina sua senha", "Recebemos uma solicitação para redefinir a senha da sua conta.\n\n" + origin + "/acessar#reset=exemplo-sem-validade\n\nEste link expira em 1 hora. Se não solicitou a alteração, ignore esta mensagem."),
            "cadastro": ("Confirme seu e-mail", "Confirme seu endereço de e-mail para continuar seu cadastro.\n\n" + origin + "/acessar#verify=exemplo-sem-validade"),
            "convite": ("Convite para a equipe Iustus", "Você recebeu um convite para acessar a equipe Iustus.\n\n" + origin + "/acessar#invite=exemplo-sem-validade"),
            "atendimento": ("Iustus: atualização no atendimento", "Há uma novidade no seu atendimento. Entre na sua conta para consultar os detalhes com segurança.\n\n" + origin + "/cliente"),
        }
        logo = "data:image/png;base64," + base64.b64encode((ROOT / "assets" / "iustus-logo.png").read_bytes()).decode()
        for name, (subject, body) in samples.items():
            (output / (name + ".html")).write_text(render_email(subject, body).replace("cid:iustus-logo", logo), encoding="utf-8")
        self.stdout.write(f"Generated {len(samples)} previews; no email sent.")
