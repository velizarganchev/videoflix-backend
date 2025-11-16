"""
Video serializer for the Videoflix API.

Provides:
- Full serialization of Video model
- image_url field returning an absolute URL (local or S3)
- Restricts video creation to superusers only
"""

from rest_framework import serializers
from content_app.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """
    Serializer for Video objects.
    Adds a computed image_url field that always returns an absolute URL.
    """

    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Video
        fields = "__all__"

    def get_image_url(self, obj):
        """
        Return an absolute URL for the thumbnail image.

        - If image_file is missing → return None.
        - If URL is relative (/media/...) → build full URL using request.
        - If using S3 → returns the S3 URL directly.
        """
        if not obj.image_file:
            return None

        request = self.context.get("request")

        try:
            url = obj.image_file.url
        except Exception:
            return None

        # Build full URL on local storage
        if request and url and url.startswith("/"):
            return request.build_absolute_uri(url)

        return url  # already absolute (e.g., S3)

    def create(self, validated_data):
        """
        Restrict API creation: only superusers can create Video objects.
        """
        request = self.context.get("request")

        if not request or not request.user.is_superuser:
            raise serializers.ValidationError(
                "You do not have permission to create a video."
            )

        return super().create(validated_data)
