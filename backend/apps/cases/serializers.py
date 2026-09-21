from rest_framework import serializers

from apps.identity.serializers import StrictSerializer
from .models import Case


class DraftInput(StrictSerializer):
    title = serializers.CharField(max_length=160, allow_blank=True, required=False)
    description = serializers.CharField(max_length=20000, allow_blank=True, required=False)
    category = serializers.ChoiceField(choices=Case.Category.choices, allow_blank=True, required=False)
    scopeAcknowledged = serializers.BooleanField(required=False)


class VersionInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)


class EditInput(DraftInput, VersionInput):
    pass


class AssignmentInput(VersionInput):
    lawyerId = serializers.UUIDField()
    reason = serializers.CharField(min_length=5, max_length=2000)


class TransitionInput(VersionInput):
    targetState = serializers.ChoiceField(choices=[Case.State.TRIAGE, Case.State.ACCEPTED, Case.State.REJECTED])
    reason = serializers.CharField(min_length=5, max_length=2000, required=False, default="")
    scopeConfirmed = serializers.BooleanField(required=False, default=False)
    conflictChecked = serializers.BooleanField(required=False, default=False)
    informationSufficient = serializers.BooleanField(required=False, default=False)


class RequestInput(VersionInput):
    description = serializers.CharField(min_length=5, max_length=4000)


class ResponseInput(VersionInput):
    text = serializers.CharField(min_length=5, max_length=10000)
    documentVersionIds = serializers.ListField(child=serializers.UUIDField(), max_length=20, required=False, default=list)


class ResolutionInput(VersionInput):
    reason = serializers.CharField(min_length=5, max_length=2000)
