from rest_framework import serializers

from apps.identity.serializers import StrictSerializer


class UploadInput(StrictSerializer):
    filename = serializers.CharField(max_length=180)
    sizeBytes = serializers.IntegerField(min_value=1, max_value=20 * 1024 * 1024)
    mime = serializers.ChoiceField(choices=["application/pdf", "image/jpeg", "image/png"])


class NewVersionInput(UploadInput):
    previousVersion = serializers.IntegerField(min_value=1)


class CompleteInput(StrictSerializer):
    checksum = serializers.RegexField(r"^[0-9a-f]{64}$")
