"""PagBank: o cartão chega apenas criptografado pelo SDK oficial no navegador."""
import base64
import json
import re
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from apps.identity.security import IdentityError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_api(path, payload=None, key=None, *, configuration_check=False):
    # A consulta da chave permite preparar a integração sem habilitar cobranças.
    if configuration_check and (path not in ("/public-keys/webhook", "/public-keys/card") or payload is not None):
        raise ValueError("Configuration checks only allow reading public keys")
    if settings.PAGBANK_ENVIRONMENT not in ("sandbox", "production"):
        raise IdentityError("INVALID_PAYMENT_ENVIRONMENT", "Configure o ambiente PagBank como sandbox ou production.", 503)
    if (not settings.BILLING_ENABLED and not configuration_check) or not settings.PAGBANK_API_TOKEN:
        raise IdentityError("BILLING_UNAVAILABLE", "A adesão online ainda não está disponível.", 503)
    base = "https://sandbox.api.pagseguro.com" if settings.PAGBANK_ENVIRONMENT == "sandbox" else "https://api.pagseguro.com"
    headers = {"Authorization": "Bearer " + settings.PAGBANK_API_TOKEN, "Accept": "application/json", "Content-Type": "application/json"}
    if key:
        headers["x-idempotency-key"] = str(key)
    req = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    try:
        with build_opener(NoRedirect).open(req, timeout=10) as response:
            result = json.loads(response.read(1048576))
        if not isinstance(result, dict):
            raise ValueError("InvalidResponse")
        return result
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise IdentityError("PAGBANK_AUTH_FAILED", "O PagBank recusou a credencial ou a permissão para esta API. Confira o token e o ambiente.", 503) from exc
        raise IdentityError("PAYMENT_PROVIDER_UNAVAILABLE", f"O PagBank retornou HTTP {exc.code}. Consulte a configuração da integração.", 503) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise IdentityError("PAYMENT_PROVIDER_UNAVAILABLE", "Não foi possível consultar o pagamento. Tente novamente.", 503) from exc


def create_checkout(order):
    origin = settings.PORTAL_ORIGINS["client"]
    webhook = origin + "/api/v1/billing/webhook"
    result = request_api("/checkouts", {
        "reference_id": str(order.pk), "customer_modifiable": True,
        "items": [{"reference_id": "iustus-associacao-anual", "name": "Adesão anual à associação Iustus", "quantity": 1, "unit_amount": order.amount}],
        "payment_methods": [{"type": "CREDIT_CARD"}, {"type": "PIX"}],
        "payment_methods_configs": [{"type": "CREDIT_CARD", "config_options": [{"option": "INSTALLMENTS_LIMIT", "value": str(order.installments)}, {"option": "INTEREST_FREE_INSTALLMENTS", "value": str(order.installments)}]}],
        "redirect_url": origin + "/checkout?retorno=1", "return_url": origin + "/checkout?retorno=1",
        "notification_urls": [webhook], "payment_notification_urls": [webhook],
    }, order.pk)
    identifier = result.get("id", "")
    url = next((link.get("href", "") for link in result.get("links", []) if link.get("rel") == "PAY"), "")
    parsed = urlsplit(url)
    if not re.fullmatch(r"CHEC_[A-Za-z0-9-]+", identifier) or parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443) or not any(parsed.hostname == host or (parsed.hostname or "").endswith("." + host) for host in ("pagbank.com.br", "pagseguro.uol.com.br")):
        raise IdentityError("INVALID_CHECKOUT", "O provedor não retornou um checkout válido.", 502)
    return identifier, url


def card_public_key():
    result = request_api("/public-keys/card")
    key = result.get("public_key")
    if not isinstance(key, str) or not 100 <= len(key) <= 8192:
        raise IdentityError("INVALID_PUBLIC_KEY", "Não foi possível preparar o pagamento com cartão.", 503)
    return key


def create_card_order(order, customer, card):
    phone = customer["phone"]
    result = request_api("/orders", {
        "reference_id": str(order.pk),
        "customer": {"name": customer["name"], "email": customer["email"], "tax_id": customer["cpf"],
            "phones": [{"country": "55", "area": phone[:2], "number": phone[2:], "type": "MOBILE"}]},
        "items": [{"reference_id": "iustus-associacao-anual", "name": "Adesão anual à associação Iustus", "quantity": 1, "unit_amount": order.amount}],
        "notification_urls": [settings.PORTAL_ORIGINS["client"] + "/api/v1/billing/webhook"],
        "charges": [{"reference_id": str(order.pk), "description": "Adesão anual Iustus",
            "amount": {"value": order.amount, "currency": "BRL"},
            "payment_method": {"type": "CREDIT_CARD", "installments": order.installments, "capture": True,
                "card": {"encrypted": card["encrypted"], "store": False},
                "holder": {"name": card["holderName"], "tax_id": card["holderCpf"]}}}],
    }, order.pk)
    identifier = result.get("id", "")
    if not isinstance(identifier, str) or not re.fullmatch(r"ORDE_[A-Za-z0-9-]+", identifier) or result.get("reference_id") != str(order.pk):
        raise IdentityError("INVALID_PAYMENT", "O pagamento está em conferência. Aguarde antes de tentar novamente.", 502)
    return identifier


def verify_signature(raw, header):
    if not header or len(header) > 4096 or not settings.PAGBANK_WEBHOOK_PUBLIC_KEY:
        return False
    try:
        key = serialization.load_der_public_key(base64.b64decode(settings.PAGBANK_WEBHOOK_PUBLIC_KEY, validate=True))
        if not isinstance(key, ec.EllipticCurvePublicKey):
            return False
    except (ValueError, TypeError):
        return False
    for value in header.split(","):
        try:
            key.verify(base64.b64decode(value.strip(), validate=True), raw, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError, TypeError):
            continue
    return False
