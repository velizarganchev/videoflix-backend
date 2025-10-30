"""
serializers.py — User Profile Serializer for Videoflix Backend

Defines the serializer for the custom `UserProfile` model,
handling registration, password validation, and token generation.

Features:
- Returns user info plus authentication token
- Validates unique email and matching passwords
- Creates users securely via `create_user()`
"""

from rest_framework import serializers
from ..models import UserProfile
from rest_framework.authtoken.models import Token


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration and profile management.

    Includes:
    - Token generation for authentication
    - Email and password validation
    - Write-only password fields for security
    """

    token = serializers.SerializerMethodField()
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'token',
            'username',
            'email',
            'phone',
            'address',
            'favorite_videos',
            'password',
            'confirm_password',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'username': {'required': False},
        }

    def get_token(self, obj):
        """
        Retrieve or create an authentication token for the user.

        Called automatically by DRF when serializing the user.
        Returns:
            str: Token key associated with the user.
        """
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

    def validate(self, data):
        """
        Validate registration data before user creation.

        Ensures:
        - Email is unique
        - Password and confirm_password match
        """
        if UserProfile.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError(
                {"email": "User with this email already exists."}
            )

        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"password": "Passwords must match."}
            )
        return data

    def create(self, validated_data):
        """
        Create a new user securely via the custom model manager.

        Removes confirm_password and passes all other validated
        fields to `UserProfile.objects.create_user()`.
        """
        validated_data.pop('confirm_password')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        is_active = validated_data.pop('is_active', False)

        # Create user through model manager (handles password hashing)
        user = UserProfile.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=is_active,
            **validated_data,
        )
        return user
