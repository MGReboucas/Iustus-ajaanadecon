"""Transporte Mercado Pago e consulta de pagamentos legados."""
import hashlib
import hmac
import json
import re
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from django.conf import settings
from apps.identity.security import IdentityError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_api(path, payload=None, key=None, *, configuration_check=False):
    if configuration_check and (path != "/users/me" or payload is not None):
        raise ValueError("Only account lookup is allowed")
    if (not settings.BILLING_ENABLED and payload is not None) or not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise IdentityError("BILLING_UNAVAILABLE", "Pagamento ainda indisponível.", 503)
    if settings.MERCADOPAGO_ENVIRONMENT not in ("sandbox", "production"):
        raise IdentityError("INVALID_PAYMENT_ENVIRONMENT", "Configure o ambiente de pagamento.", 503)
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Invalid API path")
    headers = {"Authorization": "Bearer " + settings.MERCADOPAGO_ACCESS_TOKEN,
               "Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["X-Idempotency-Key"] = str(key)
    if path.startswith("/v1/payments"):
        headers["X-Expand-Response-Nodes"] = "gateway.reference"
    req = Request("https://api.mercadopago.com" + path, headers=headers,
                  data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with build_opener(NoRedirect).open(req, timeout=8) as response:
            result = json.loads(response.read(1048576))
        if not isinstance(result, dict):
            raise ValueError("Invalid response")
        return result
    except HTTPError as exc:
        # Orders can exist even when processing returns 402. Retain the ID and
        # reconcile with GET; never turn a decline into a new uncertain charge.
        if path == "/v1/orders" and exc.code == 402 and isinstance(payload, dict):
            try:
                result = json.loads(exc.read(1048576))
                if (isinstance(result, dict) and re.fullmatch(r"ORD[A-Z0-9]{26}", str(result.get("id", "")))
                        and result.get("external_reference") == payload.get("external_reference")):
                    return result
            except (ValueError, TypeError):
                pass
        raise IdentityError("PAYMENT_PROVIDER_UNAVAILABLE", "Não foi possível consultar o Mercado Pago. Tente novamente.", 503) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        # Não expor corpo de erro, dados pessoais ou credencial.
        raise IdentityError("PAYMENT_PROVIDER_UNAVAILABLE", "Não foi possível consultar o Mercado Pago. Tente novamente.", 503) from exc


def identifier(value):
    value = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise IdentityError("INVALID_PROVIDER_RESPONSE", "Resposta do pagamento inválida.", 502)
    return value


def payment(payment_id):
    if not re.fullmatch(r"[0-9]{1,30}", str(payment_id)):
        raise IdentityError("INVALID_PAYMENT", "Identificador do pagamento inválido.", 422)
    return request_api("/v1/payments/" + str(payment_id))


def cents(value):
    try:
        number = Decimal(str(value)) * 100
        if not number.is_finite() or number != number.to_integral_value():
            raise ValueError()
        return int(number)
    except (ValueError, InvalidOperation, TypeError):
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "Valor do pagamento inválido.", 422)


def validate_payment(order, snapshot, instrument):
    if (str(snapshot.get("external_reference")) != str(order.pk)
            or str(snapshot.get("collector_id")) != str(settings.MERCADOPAGO_COLLECTOR_ID)
            or snapshot.get("live_mode") is not (order.environment == "production")
            or str(snapshot.get("payer", {}).get("id")) != instrument["customerId"]):
        raise IdentityError("PAYMENT_MISMATCH", "Pagamento não corresponde à contratação.", 422)
    if (snapshot.get("currency_id") != "BRL" or cents(snapshot.get("transaction_amount")) != order.amount
            or snapshot.get("installments") != order.installments
            or snapshot.get("payment_type_id") != "credit_card"):
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "Condições de pagamento divergentes.", 422)
    if snapshot.get("status") == "approved" and cents(snapshot.get("transaction_details", {}).get("total_paid_amount")) != order.amount:
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "O pagamento não corresponde ao total sem juros contratado.", 422)


def verify_signature(payment_id, request_id, signature):
    if not settings.MERCADOPAGO_WEBHOOK_SECRET or not re.fullmatch(r"(?:[0-9]{1,30}|ORD[A-Z0-9]{26})", payment_id or ""):
        return False
    if not request_id or len(request_id) > 200 or len(signature) > 1000:
        return False
    try:
        parts = dict(part.strip().split("=", 1) for part in signature.split(","))
        ts, value = parts["ts"], parts["v1"]
        if not ts.isdigit() or not re.fullmatch(r"[a-fA-F0-9]{64}", value):
            return False
    except (ValueError, KeyError):
        return False
    manifest = f"id:{payment_id};request-id:{request_id};ts:{ts};"
    expected = hmac.new(settings.MERCADOPAGO_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, value.lower())
