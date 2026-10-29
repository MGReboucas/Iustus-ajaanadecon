"""Server-only REST adapter for a private, dedicated demonstration bucket."""
import io
import json
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from django.conf import settings
from apps.identity.security import IdentityError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(path, method="GET", data=None, content_type="application/octet-stream"):
    headers = {"Authorization": "Bearer " + settings.DOCUMENT_SUPABASE_SERVICE_KEY,
               "apikey": settings.DOCUMENT_SUPABASE_SERVICE_KEY,
               "Content-Type": content_type, "x-upsert": "false"}
    req = Request(settings.DOCUMENT_SUPABASE_URL + "/storage/v1/" + path,
                  data=data, headers=headers, method=method)
    try:
        return build_opener(NoRedirect()).open(req, timeout=30)
    except (HTTPError, URLError, TimeoutError):
        # Never expose provider response bodies, credentials or private object URLs.
        raise IdentityError("DOCUMENT_STORAGE_UNAVAILABLE", "Armazenamento indisponível. Confira a configuração do Supabase.", 503) from None


def private_bucket():
    with request("bucket/" + settings.DOCUMENT_SUPABASE_BUCKET) as response:
        metadata = json.loads(response.read(65536))
    if metadata.get("public") is not False:
        raise IdentityError("PRIVATE_BUCKET_REQUIRED", "Configure o bucket de demonstração como privado.", 503)


def path(key):
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ValueError("Invalid object key")
    return "object/" + settings.DOCUMENT_SUPABASE_BUCKET + "/demo/" + key


def write(key, stream, expected_size):
    from .private import InvalidFile
    if not 1 <= expected_size <= 3 * 1024 * 1024:
        raise InvalidFile("size")
    content = stream.read(expected_size + 1)
    if len(content) != expected_size:
        raise InvalidFile("size")
    private_bucket()
    with request(path(key), "POST", content):
        pass


def read(key):
    private_bucket()
    with request(path(key)) as response:
        content = response.read(3 * 1024 * 1024 + 1)
    if len(content) > 3 * 1024 * 1024:
        raise IdentityError("INVALID_FILE", "Arquivo excede o limite da demonstração.", 422)
    return io.BytesIO(content)


def delete(key):
    path(key)  # Validate before constructing the delete payload.
    private_bucket()
    payload = json.dumps({"prefixes": ["demo/" + key]}).encode()
    with request("object/" + settings.DOCUMENT_SUPABASE_BUCKET, "DELETE", payload, "application/json"):
        pass
