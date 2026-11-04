"""Payments API e cartões no cofre do Mercado Pago, sem PAN/CVV no backend."""
import hashlib
import hmac
import json
import re
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        # Não expor corpo de erro, dados pessoais ou credencial.
        raise IdentityError("PAYMENT_PROVIDER_UNAVAILABLE", "Não foi possível consultar o Mercado Pago. Tente novamente.", 503) from exc


def identifier(value):
    value = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise IdentityError("INVALID_PROVIDER_RESPONSE", "Resposta do pagamento inválida.", 502)
    return value


def prepare_instrument(customer, card, subscription_id):
    result = request_api("/v1/customers/search?" + urlencode({"email": customer["email"]}))
    rows = result.get("results", [])
    found = next((row for row in rows if row.get("email", "").lower() == customer["email"]), None)
    if not found:
        found = request_api("/v1/customers", {"email": customer["email"], "first_name": customer["name"]}, str(subscription_id) + "-customer")
    customer_id = identifier(found.get("id"))
    saved = request_api(f"/v1/customers/{customer_id}/cards", {"token": card["token"],
        "payment_method_id": card["paymentMethodId"], "issuer_id": card["issuerId"]}, str(subscription_id) + "-card")
    if (str(saved.get("user_id")) != str(settings.MERCADOPAGO_COLLECTOR_ID)
            or str(saved.get("customer_id")) != customer_id
            or saved.get("live_mode") is not (settings.MERCADOPAGO_ENVIRONMENT == "production")):
        raise IdentityError("PAYMENT_MISMATCH", "Conta recebedora ou ambiente do cartão divergente.", 422)
    if saved.get("payment_method", {}).get("payment_type_id") != "credit_card":
        raise IdentityError("CREDIT_CARD_REQUIRED", "Use um cartão de crédito para o plano anual parcelado.", 422)
    return {"customerId": customer_id, "cardId": identifier(saved.get("id")),
            "paymentMethodId": identifier(saved.get("payment_method", {}).get("id")),
            "issuerId": identifier(saved.get("issuer", {}).get("id"))}


def payment_payload(order, subscription, instrument):
    token = identifier(request_api("/v1/card_tokens", {"card_id": instrument["cardId"]}).get("id"))
    data = {"first_transaction": order.cycle == 0, "storage": "stored",
            "transaction_initiator": "customer" if order.cycle == 0 else "merchant",
            "subscription_id": str(subscription.pk)}
    if instrument.get("networkTransactionId"):
        data["network_transaction_id"] = instrument["networkTransactionId"]
    return {"token": token, "transaction_amount": order.amount / 100, "installments": order.installments,
            "payment_method_id": instrument["paymentMethodId"], "issuer_id": instrument["issuerId"],
            "payer": {"type": "customer", "id": instrument["customerId"]},
            "description": "Associação anual Iustus", "external_reference": str(order.pk),
            "notification_url": settings.PORTAL_ORIGINS["client"] + "/api/v1/billing/mercadopago/webhook",
            "point_of_interaction": {"type": "CREDENTIAL_ON_FILE", "sub_type": "recurring", "transaction_data": data}}


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
    if not settings.MERCADOPAGO_WEBHOOK_SECRET or not re.fullmatch(r"[0-9]{1,30}", payment_id or ""):
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
