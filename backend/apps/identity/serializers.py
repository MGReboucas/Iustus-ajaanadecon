from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Envie um objeto JSON.")
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: "Campo não permitido." for key in unknown})
        return super().to_internal_value(data)


class EmailSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return value.strip().lower()


class RegisterSerializer(EmailSerializer):
    name = serializers.CharField(min_length=2, max_length=150)
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False, write_only=True)
    policyVersion = serializers.CharField(max_length=80)


class LoginSerializer(EmailSerializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class TokenSerializer(StrictSerializer):
    token = serializers.CharField(min_length=20, max_length=256, write_only=True)


class ResetSerializer(TokenSerializer):
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False, write_only=True)


class AcceptInviteSerializer(ResetSerializer):
    name = serializers.CharField(min_length=2, max_length=150)


class CodeSerializer(StrictSerializer):
    code = serializers.CharField(min_length=6, max_length=64, write_only=True)


class ProfileSerializer(StrictSerializer):
    name = serializers.CharField(min_length=2, max_length=150)
    caseEmailEnabled = serializers.BooleanField()
