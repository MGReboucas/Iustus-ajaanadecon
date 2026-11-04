import logging
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.views import exception_handler


def identity_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    if response.status_code >= 500:
        logging.getLogger("django.request").error(
            "Handled API exception", exc_info=(type(exc), exc, exc.__traceback__),
            extra={"status_code": response.status_code},
        )
    code = getattr(exc, "identity_code", None)
    if code is None:
        code = "AUTH_REQUIRED" if isinstance(exc, NotAuthenticated) else "FORBIDDEN" if isinstance(exc, PermissionDenied) else "NOT_FOUND" if isinstance(exc, NotFound) else "INVALID_INPUT"
    original = response.data
    detail = original.get("detail") if isinstance(original, dict) else None
    response.data = {"error": {"code": code, "message": str(detail or "Confira os dados informados."), "fields": {} if detail else original}}
    if response.status_code == 429:
        response["Retry-After"] = "300"
    return response
