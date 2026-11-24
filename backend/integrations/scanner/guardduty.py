"""Read-only scan verdicts. Only AWS's explicit clean result permits release."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from integrations.storage.private import remote_key, s3_client


def verdict(key):
    if settings.DOCUMENT_STORAGE_BACKEND != "s3":
        raise ImproperlyConfigured("GuardDuty requires AWS S3")
    response = s3_client(quick=True).get_object_tagging(
        Bucket=settings.DOCUMENT_S3_BUCKET, Key=remote_key(key))
    values = [tag["Value"] for tag in response.get("TagSet", [])
              if tag.get("Key") == "GuardDutyMalwareScanStatus"]
    if not values:
        return "QUARANTINED", ""
    if values == ["NO_THREATS_FOUND"]:
        return "AVAILABLE", ""
    if values == ["THREATS_FOUND"]:
        return "REJECTED", "MALWARE_DETECTED"
    if values == ["UNSUPPORTED"]:
        return "REJECTED", "SCAN_UNSUPPORTED"
    # Includes denied access, failed scans and unexpected/malformed statuses.
    return "ERROR", "GUARDDUTY_UNAVAILABLE"
