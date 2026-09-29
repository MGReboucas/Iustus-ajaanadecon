"""Auditoria de configuração S3 e teste sintético do scanner; sem gravar objetos."""
from io import BytesIO
from urllib.parse import urlsplit

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from integrations.scanner.clamav import scan
from integrations.storage.private import s3_client


REQUIRED_HEADERS = {"content-type", "if-none-match", "x-amz-checksum-sha256",
                    "x-amz-server-side-encryption"}
PUBLIC_FLAGS = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")


def check_storage():
    if settings.DOCUMENT_STORAGE_BACKEND != "s3" or not settings.DOCUMENT_S3_BUCKET:
        raise CommandError("Configure DOCUMENT_STORAGE_BACKEND=s3 e o bucket de homologação.")
    origins = set(settings.PORTAL_ORIGINS.values())
    if len(origins) != 2 or any(urlsplit(origin).scheme != "https" for origin in origins):
        raise CommandError("Configure duas origens HTTPS distintas para os portais.")
    client, bucket = s3_client(), settings.DOCUMENT_S3_BUCKET
    block = client.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    if not all(block.get(flag) is True for flag in PUBLIC_FLAGS):
        raise CommandError("Ative os quatro bloqueios de acesso público no bucket.")
    ownership = client.get_bucket_ownership_controls(Bucket=bucket)["OwnershipControls"]["Rules"]
    if not any(rule.get("ObjectOwnership") == "BucketOwnerEnforced" for rule in ownership):
        raise CommandError("Configure Object Ownership como Bucket owner enforced.")
    try:
        policy = client.get_bucket_policy_status(Bucket=bucket)["PolicyStatus"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchBucketPolicy":
            raise
    else:
        if policy.get("IsPublic") is not False:
            raise CommandError("A política do bucket permite acesso público ou não pôde ser validada.")
    covered = set()
    for rule in client.get_bucket_cors(Bucket=bucket)["CORSRules"]:
        allowed = set(rule.get("AllowedOrigins", []))
        headers = {value.lower() for value in rule.get("AllowedHeaders", [])}
        if not allowed or not allowed <= origins or set(rule.get("AllowedMethods", [])) != {"PUT"}:
            raise CommandError("CORS deve permitir somente PUT nas duas origens dos portais.")
        if not REQUIRED_HEADERS <= headers or any("*" in value for value in headers):
            raise CommandError("CORS deve permitir os quatro headers de upload sem curingas.")
        covered.update(allowed)
    if covered != origins:
        raise CommandError("CORS incompleto: configure ambos os portais.")


def check_scanner():
    # Amostra limpa e padrão inofensivo EICAR apenas em memória; não grava arquivo.
    clean = b"%PDF-1.4\\nIustus synthetic scanner check\\n%%EOF\\n"
    eicar = (b"X5O!P%@AP[4" + bytes([92]) + b"PZX54(P^)7CC)7}$"
             + b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")
    if scan(BytesIO(clean)) is not True:
        raise CommandError("O scanner não liberou a amostra limpa.")
    if scan(BytesIO(eicar)) is not False:
        raise CommandError("O scanner não bloqueou o padrão de teste EICAR.")


class Command(BaseCommand):
    help = "Confere S3 privado/CORS e ClamAV, sem gravar objetos nem alterar configurações."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--only", choices=("storage", "scanner"))

    def handle(self, *args, **options):
        failures = []
        for name, check in (("storage", check_storage), ("scanner", check_scanner)):
            if options["only"] and options["only"] != name:
                continue
            try:
                check()
            except CommandError as exc:
                failures.append(f"{name}: {exc}")
            except Exception:
                # Exceções de SDK/rede podem conter URL, host, assinatura ou credenciais.
                failures.append(f"{name}: falha de conexão, permissão ou API incompatível; confira a configuração do serviço.")
            else:
                self.stdout.write(f"{name}: OK")
        if failures:
            raise CommandError("\n".join(failures))
        self.stdout.write("Pré-checagem concluída. Ainda é necessário validar PUT assinado e o fluxo no navegador.")
