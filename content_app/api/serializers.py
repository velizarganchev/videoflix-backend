"""
content_app.serializers — Video serializer for Videoflix backend

Purpose:
--------
Defines serialization logic for the Video model, including creation permissions.

Features:
- Serializes all fields of the Video model
- Restricts creation to superusers only (security measure)
"""

from rest_framework import serializers
from content_app.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """
    Serializer for Video objects.

    Provides:
        - Full serialization of all Video fields
        - Validation during creation to restrict non-admin users
    """

    class Meta:
        model = Video
        fields = "__all__"

    def create(self, validated_data):
        """
        Create a new Video instance.

        Restricts creation to superusers only.
        If a non-superuser attempts to create a video,
        a ValidationError is raised.

        Args:
            validated_data (dict): Validated video data.

        Returns:
            Video: The created video instance.
        """
        request = self.context.get("request")

        # Only superusers are allowed to create new videos
        if not request or not request.user.is_superuser:
            raise serializers.ValidationError(
                "You do not have permission to create a video."
            )

        return super().create(validated_data)
