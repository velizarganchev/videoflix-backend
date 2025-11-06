"""
Serializers for Videoflix Users (JWT cookies only, no DRF Token).

- RegisterSerializer: handles user registration and password validation.
- LoginSerializer: validates user credentials; JWT tokens are issued in the view.
- UserPublicSerializer: exposes safe, public user data for list/detail responses.
"""

from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from ..models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    """
    Responsibilities:
    - Validates unique email and matching passwords.
    - Creates an inactive user instance (activation via email confirmation).
    - Username is not exposed; it is auto-filled with the email.
    """
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=UserProfile.objects.all(),
                message="User with this email already exists.",
            )
        ]
    )
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"})

    class Meta:
        model = UserProfile
        fields = ["id", "email", "phone", "address",
                  "password", "confirm_password"]
        extra_kwargs = {"email": {"required": True}}

    def validate(self, data):
        """
        - Normalize email.
        - Ensure password confirmation matches.
        - Run Django's password validators.
        """
        data["email"] = data["email"].strip().lower()

        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError(
                {"password": "Passwords must match."})

        password_validation.validate_password(data["password"])
        return data

    def create(self, validated_data):
        """
        Create a new inactive user:
        - username is auto-set to the email
        - 'is_active' can be injected via serializer.save(is_active=False) in the view
        """
        validated_data.pop("confirm_password")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        is_active = validated_data.pop("is_active", False)

        user = UserProfile.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=is_active,
            **validated_data,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials (input-only).
    Tokens are created and set as HttpOnly cookies in the view.
    """
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        """
        Normalize email and authenticate using Django's auth system.
        """
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password")

        user = authenticate(username=email, password=password)
        if not user or not user.is_active:
            raise serializers.ValidationError(
                "Invalid credentials or inactive user.")

        attrs["user"] = user
        return attrs


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Public-facing serializer for user profiles.
    Excludes sensitive fields such as password or permissions.
    """
    class Meta:
        model = UserProfile
        fields = ["id", "username", "email", "phone", "address"]
        read_only_fields = fields
