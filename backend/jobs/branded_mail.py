"""Shared multipart email design with an embedded logo and a plain-text fallback."""
import re
from email.mime.image import MIMEImage
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Engine

ROOT = Path(__file__).resolve().parent


def canonical_body(body):
    # Rewrite only the former first-party portal, including already queued links.
    return re.sub(r"https://iustus-defesa-juridica\.vercel\.app(?=/|[\s]|$)",
                  "https://iustus.app", body)


def render_email(subject, body):
    origins = {urlsplit(origin).netloc for origin in settings.PORTAL_ORIGINS.values()}
    links = re.findall(r"https?://[^\s<>]+", body)
    url = next((link for link in links if urlsplit(link).netloc in origins
                and not urlsplit(link).username and not urlsplit(link).password), "")
    label = "Acessar minha conta"
    for marker, title in (("#member=", "Concluir meu cadastro"), ("#verify=", "Confirmar meu e-mail"),
                          ("#reset=", "Redefinir minha senha"), ("#invite=", "Ativar meu acesso")):
        if marker in url:
            label = title
            break
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip() and part.strip() != url
                  and part.strip() != subject]
    template = Engine().from_string((ROOT / "templates" / "email.html").read_text(encoding="utf-8"))
    return template.render(Context({"subject": subject, "paragraphs": paragraphs, "url": url, "label": label}))


def build_message(subject, body, recipients, headers=None):
    body = canonical_body(body)
    message = EmailMultiAlternatives(subject, body, None, recipients, headers=headers)
    message.attach_alternative(render_email(subject, body), "text/html")
    message.mixed_subtype = "related"
    logo = MIMEImage((ROOT / "assets" / "iustus-logo.png").read_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<iustus-logo>")
    logo.add_header("Content-Disposition", "inline", filename="iustus-logo.png")
    message.attach(logo)
    return message
