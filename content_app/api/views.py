from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import Video
from .serializers import VideoSerializer


class GetContentItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        content = Video.objects.all()
        serializer = VideoSerializer(content, many=True)
        return Response(serializer.data)


class GetSingleContentItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        content = Video.objects.get(pk=pk)
        serializer = VideoSerializer(content)
        return Response(serializer.data)


class AddFavoriteVideoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        video_id = request.data.get('video_id')

        if not video_id:
            return Response({'message': 'Video ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = Video.objects.get(pk=video_id)

            if video in user.favorite_videos.all():
                user.favorite_videos.remove(video)
                favorite_videos = user.favorite_videos.values_list(
                    'id', flat=True)
                favorite_videos_ids = list(favorite_videos)

                return Response(favorite_videos_ids, status=status.HTTP_200_OK)

            user.favorite_videos.add(video)
            favorite_videos = user.favorite_videos.values_list('id', flat=True)
            favorite_videos_ids = list(favorite_videos)

            return Response(favorite_videos_ids, status=status.HTTP_200_OK)

        except Video.DoesNotExist:
            return Response({"message": "Video not found"}, status=status.HTTP_404_NOT_FOUND)
