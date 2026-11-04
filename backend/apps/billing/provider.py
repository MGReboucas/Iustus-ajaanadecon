from django.conf import settings


def environment(provider=None):
    return settings.MERCADOPAGO_ENVIRONMENT if (provider or settings.BILLING_PROVIDER) == "mercadopago" else settings.PAGBANK_ENVIRONMENT


def available():
    if settings.BILLING_PROVIDER == "mercadopago":
        return bool(settings.BILLING_ENABLED and settings.MERCADOPAGO_ACCESS_TOKEN
                    and settings.MERCADOPAGO_PUBLIC_KEY and settings.MERCADOPAGO_WEBHOOK_SECRET
                    and settings.MERCADOPAGO_COLLECTOR_ID
                    and settings.MERCADOPAGO_INTEREST_FREE_CONFIRMED
                    and settings.MERCADOPAGO_ENVIRONMENT in ("sandbox", "production"))
    return settings.BILLING_ENABLED and settings.BILLING_PROVIDER == "pagbank"
