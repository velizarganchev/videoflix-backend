from rest_framework import serializers
from content_app.models import Video


class VideoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Video
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_superuser:
            raise serializers.ValidationError(
                'You do not have permission to create a video.'
            )
        return super().create(validated_data)
