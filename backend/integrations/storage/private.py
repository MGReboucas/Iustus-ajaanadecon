"""Armazenamento local privado, habilitado apenas em desenvolvimento/testes.

Nenhuma URL estática é emitida. A API revalida sessão e vínculo antes da leitura.
"""
import hashlib
import re
import uuid
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


def write_stream(key, stream, expected_size):
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
    with object_path(key).open("rb") as source:
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
