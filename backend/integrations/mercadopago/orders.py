"""Orders API adapter. Amounts are decimal strings; no PAN/CVV reaches this module."""
import re
from decimal import Decimal
from django.conf import settings
from apps.identity.security import IdentityError
from . import client as legacy
from .client import ORDER_ID, request_api, identifier, cents, verify_signature


def check_account():
    account = request_api("/users/me", configuration_check=True)
    if (str(account.get("id")) != str(settings.MERCADOPAGO_COLLECTOR_ID)
            or ("test_user" in account.get("tags", [])) != (settings.MERCADOPAGO_ENVIRONMENT == "sandbox")):
        raise IdentityError("PAYMENT_MISMATCH", "Conta recebedora ou ambiente divergente.", 422)
    return account


def prepare_instrument(customer, card, subscription_id):
    check_account()
    return {"payerEmail": customer["email"], "paymentMethodId": identifier(card["paymentMethodId"])}


def payment_payload(order, subscription, instrument, card=None):
    if order.cycle or not card:
        raise IdentityError("MANUAL_PAYMENT_REQUIRED", "Faça uma nova compra para renovar a associação.", 409)
    amount = format(Decimal(order.amount) / 100, ".2f")
    return {"type": "online", "processing_mode": "automatic", "total_amount": amount,
            "external_reference": str(order.pk), "payer": {"email": instrument["payerEmail"]},
            "transactions": {"payments": [{"amount": amount, "payment_method": {
                "id": instrument["paymentMethodId"], "type": "credit_card",
                "installments": order.installments, "token": identifier(card["token"])}}]}}


def create_order(payload, key):
    # Recheck even on retries: credentials can change after a timeout.
    check_account()
    return request_api("/v1/orders", payload, key)


def normalize(snapshot):
    """Normalize authenticated Orders responses to the internal billing state contract."""
    if not re.fullmatch(ORDER_ID, str(snapshot.get("id", ""))) or snapshot.get("type") != "online":
        raise IdentityError("INVALID_PAYMENT", "Resposta de order inválida.", 502)
    payments = snapshot.get("transactions", {}).get("payments", [])
    if not isinstance(payments, list) or len(payments) != 1 or not isinstance(payments[0], dict):
        raise IdentityError("PAYMENT_MISMATCH", "Quantidade de transações divergente.", 422)
    tx = payments[0]
    method = tx.get("payment_method", {})
    state, detail = snapshot.get("status"), snapshot.get("status_detail")
    status = "pending"
    if state == "processed" and detail == "accredited" and tx.get("status") == "processed" and tx.get("status_detail") == "accredited":
        status = "approved"
    elif state == "failed":
        status = "rejected"
    elif state in ("canceled", "cancelled", "expired"):
        status = "cancelled"
    elif state in ("refunded", "partially_refunded") or tx.get("status") in ("refunded", "partially_refunded") or detail == "partially_refunded" or tx.get("status_detail") == "partially_refunded":
        status = "refunded"
    elif state == "charged_back" or tx.get("status") == "charged_back" or snapshot.get("transactions", {}).get("chargebacks"):
        status = "charged_back"
    if snapshot.get("transactions", {}).get("chargebacks") or tx.get("status") == "charged_back":
        status = "charged_back"
    if tx.get("status_detail") == "partially_refunded" or tx.get("status") == "refunded":
        status = "refunded"
    if cents(tx.get("amount")) != cents(snapshot.get("total_amount")):
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "Valor da transação divergente.", 422)
    if status == "approved" and cents(tx.get("paid_amount")) != cents(snapshot.get("total_amount")):
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "Valor pago divergente.", 422)
    if method.get("installment_amount") is not None and abs(cents(method["installment_amount"]) * method.get("installments", 0) - cents(snapshot.get("total_amount"))) > method.get("installments", 0):
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "Parcelamento com valor divergente.", 422)
    return {"id": snapshot["id"], "external_reference": snapshot.get("external_reference"),
            "collector_id": snapshot.get("user_id"), "currency_id": "BRL" if snapshot.get("country_code") == "BRA" and snapshot.get("currency_id", "BRL") == "BRL" else None,
            "live_mode": snapshot.get("live_mode", settings.MERCADOPAGO_ENVIRONMENT == "production"),
            "payer": {"id": snapshot.get("payer", {}).get("customer_id"), "email": snapshot.get("payer", {}).get("email")},
            "transaction_amount": snapshot.get("total_amount"), "installments": method.get("installments"),
            "payment_type_id": method.get("type"), "transaction_details": {"total_paid_amount": snapshot.get("total_paid_amount")},
            "transaction_amount_refunded": snapshot.get("total_refunded_amount", "0"),
            "status": status, "date_approved": snapshot.get("last_updated_date"),
            "paymentProfileId": tx.get("automatic_payments", {}).get("payment_profile_id"),
            "transactionReference": tx.get("reference_id"), "orders_api": True}


def payment(payment_id):
    # Existing numeric Payments IDs remain read-only; all new charges use Orders.
    if re.fullmatch(r"[0-9]{1,30}", str(payment_id)):
        return legacy.payment(payment_id)
    if not re.fullmatch(ORDER_ID, str(payment_id)):
        raise IdentityError("INVALID_PAYMENT", "Identificador de order inválido.", 422)
    check_account()
    snapshot = request_api("/v1/orders/" + payment_id)
    if snapshot.get("id") != payment_id:
        raise IdentityError("PAYMENT_MISMATCH", "Identificador de order divergente.", 422)
    return normalize(snapshot)


def validate_payment(order, snapshot, instrument):
    if not snapshot.get("orders_api"):
        return legacy.validate_payment(order, snapshot, instrument)
    if (order.provider_order_id and str(snapshot.get("id")) != str(order.provider_order_id)
            or snapshot.get("payer", {}).get("email") not in (None, instrument.get("payerEmail"))):
        raise IdentityError("PAYMENT_MISMATCH", "Order ou pagador divergente.", 422)
    expected = instrument.get("customerId") or instrument.get("payerEmail")
    verified = dict(snapshot, payer={"id": expected})
    legacy.validate_payment(order, verified, {"customerId": expected})
