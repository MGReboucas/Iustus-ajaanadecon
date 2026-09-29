"""Armazenamento privado: disco local no desenvolvimento e S3 opcional.

Nenhuma URL estática é emitida. A API revalida sessão e vínculo antes da leitura.
"""
import hashlib
import re
import uuid
import base64
from tempfile import SpooledTemporaryFile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class InvalidFile(ValueError):
    pass


def object_path(key):
    root = getattr(settings, "DOCUMENT_STORAGE_ROOT", None)
    if not root or not settings.DOCUMENT_LOCAL_STORAGE_ENABLED:
        raise ImproperlyConfigured("Private document storage is not configured")
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ValueError("Invalid object key")
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / key
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("Invalid object path")
    return path


def _write_local(key, stream, expected_size):
    target = object_path(key)
    temp = target.with_name(uuid.uuid4().hex + ".part")
    count = 0
    try:
        with temp.open("xb") as output:
            while chunk := stream.read(min(65536, expected_size - count + 1)):
                count += len(chunk)
                if count > expected_size:
                    raise InvalidFile("size")
                output.write(chunk)
        if count != expected_size:
            raise InvalidFile("size")
        # A transação mantém o lock do caso; objetos publicados nunca são sobrescritos.
        if target.exists():
            raise InvalidFile("already_uploaded")
        temp.rename(target)
    finally:
        temp.unlink(missing_ok=True)


def inspect_file(key, expected_size):
    digest = hashlib.sha256()
    size = 0
    prefix = b""
    with open_object(key) as source:
        while chunk := source.read(65536):
            if not prefix:
                prefix = chunk[:16]
            size += len(chunk)
            if size > expected_size:
                raise InvalidFile("size")
            digest.update(chunk)
    if size != expected_size:
        raise InvalidFile("size")
    if prefix.startswith(b"%PDF-"):
        mime = "application/pdf"
    elif prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif prefix.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        raise InvalidFile("format")
    return digest.hexdigest(), mime


def storage_configured():
    backend = settings.DOCUMENT_STORAGE_BACKEND
    return bool((backend == "s3" and settings.DOCUMENT_S3_BUCKET) or
                (backend == "local" and settings.DOCUMENT_LOCAL_STORAGE_ENABLED and settings.DOCUMENT_STORAGE_ROOT))


def remote_key(key):
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ValueError("Invalid object key")
    prefix = settings.DOCUMENT_S3_PREFIX.strip("/")
    if not prefix or not re.fullmatch(r"[A-Za-z0-9/_-]+", prefix):
        raise ImproperlyConfigured("Invalid storage prefix")
    return prefix + "/" + key


def s3_client():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", endpoint_url=settings.DOCUMENT_S3_ENDPOINT or None,
        region_name=settings.DOCUMENT_S3_REGION,
        aws_access_key_id=settings.DOCUMENT_S3_ACCESS_KEY or None,
        aws_secret_access_key=settings.DOCUMENT_S3_SECRET_KEY or None,
        config=Config(connect_timeout=5, read_timeout=30, retries={"mode": "standard", "max_attempts": 2},
                      s3={"addressing_style": settings.DOCUMENT_S3_ADDRESSING_STYLE}))


def open_object(key):
    if settings.DOCUMENT_STORAGE_BACKEND != "s3":
        return object_path(key).open("rb")
    from botocore.exceptions import ClientError
    try:
        return s3_client().get_object(Bucket=settings.DOCUMENT_S3_BUCKET, Key=remote_key(key))["Body"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("NoSuchKey", "404", "NotFound"):
            raise FileNotFoundError(key) from exc
        raise


def delete_object(key):
    if settings.DOCUMENT_STORAGE_BACKEND != "s3":
        object_path(key).unlink(missing_ok=True)
    else:
        s3_client().delete_object(Bucket=settings.DOCUMENT_S3_BUCKET, Key=remote_key(key))


def write_stream(key, stream, expected_size):
    if not storage_configured():
        raise ImproperlyConfigured("Private document storage is not configured")
    if expected_size < 1 or expected_size > 200 * 1024 * 1024:
        raise InvalidFile("size")
    if settings.DOCUMENT_STORAGE_BACKEND != "s3":
        return _write_local(key, stream, expected_size)
    from botocore.exceptions import ClientError
    # Conferir tamanho e hash antes de enviar; não persistir uploads parciais no bucket.
    count, checksum = 0, hashlib.sha256()
    with SpooledTemporaryFile(max_size=4*1024*1024, mode="w+b") as content:
        while chunk := stream.read(min(65536, expected_size-count+1)):
            count += len(chunk)
            if count > expected_size:
                raise InvalidFile("size")
            checksum.update(chunk)
            content.write(chunk)
        if count != expected_size:
            raise InvalidFile("size")
        content.seek(0)
        try:
            s3_client().put_object(Bucket=settings.DOCUMENT_S3_BUCKET, Key=remote_key(key), Body=content,
                ContentLength=count, ContentType="application/octet-stream", IfNoneMatch="*",
                ServerSideEncryption="AES256", ChecksumSHA256=base64.b64encode(checksum.digest()).decode(),
                Metadata={"sha256": checksum.hexdigest()})
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("PreconditionFailed", "ConditionalRequestConflict", "412", "409"):
                raise InvalidFile("already_uploaded") from exc
            raise
