from rest_framework import serializers

from apps.identity.serializers import StrictSerializer
from .models import Message


class MessageInput(StrictSerializer):
    text = serializers.CharField(min_length=1, max_length=10000)
    visibility = serializers.ChoiceField(choices=Message.Visibility.choices, default=Message.Visibility.PUBLIC)
    clientMessageId = serializers.UUIDField()


class ReadInput(StrictSerializer):
    pass
