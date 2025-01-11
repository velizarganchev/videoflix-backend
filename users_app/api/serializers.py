from rest_framework import serializers
from ..models import UserProfile
from rest_framework.authtoken.models import Token


class UserProfileSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'token', 'username', 'email', 'phone',
                  'address', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"password": "Passwords must match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        is_active = validated_data.pop('is_active', False)
        user = UserProfile.objects.create_user(
            username=email, email=email, password=password, is_active=is_active, **validated_data
        )
        return user
