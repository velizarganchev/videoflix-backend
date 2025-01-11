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
