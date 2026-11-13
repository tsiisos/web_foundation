from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    is_customer = serializers.BooleanField(default=True)
    is_provider = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "is_customer", "is_provider")

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if not (attrs["is_customer"] or attrs["is_provider"]):
            raise serializers.ValidationError("Choose at least one role.")
        candidate = User(
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        validate_password(attrs["password"], candidate)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name",
            "is_customer", "is_provider", "is_email_verified", "date_joined",
        )
        read_only_fields = (
            "id", "email", "is_customer", "is_provider", "is_email_verified", "date_joined",
        )


class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("is_customer", "is_provider")

    def validate(self, attrs):
        customer = attrs.get("is_customer", self.instance.is_customer)
        provider = attrs.get("is_provider", self.instance.is_provider)
        if not (customer or provider):
            raise serializers.ValidationError("Choose at least one role.")
        return attrs


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].lower()
        return super().validate(attrs)


class UidTokenSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(UidTokenSerializer):
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
