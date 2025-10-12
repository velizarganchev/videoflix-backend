from django.conf import settings
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from urllib.parse import quote

import boto3

from ..models import Video
from .serializers import VideoSerializer

# ----- Cache TTL -----
CACHE_TTL = getattr(settings, "CACHE_TTL", DEFAULT_TIMEOUT)


# ==========================
# LIST + DETAIL
# ==========================
class GetContentItemsView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(CACHE_TTL))
    def get(self, request):
        qs = Video.objects.all()
        ser = VideoSerializer(qs, many=True)
        return Response(ser.data)


class GetSingleContentItemView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            obj = Video.objects.get(pk=pk)
        except Video.DoesNotExist:
            raise Http404("Video not found")
        ser = VideoSerializer(obj)
        return Response(ser.data)


# ==========================
# FAVORITES TOGGLE
# ==========================
class AddFavoriteVideoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        video_id = request.data.get("video_id")
        if not video_id:
            return Response(
                {"message": "Video ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            video = Video.objects.get(pk=video_id)
        except Video.DoesNotExist:
            return Response(
                {"message": "Video not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if video in user.favorite_videos.all():
            user.favorite_videos.remove(video)
        else:
            user.favorite_videos.add(video)

        ids = list(user.favorite_videos.values_list("id", flat=True))
        return Response(ids, status=status.HTTP_200_OK)


# ==========================
# SIGNED / PUBLIC URLs FOR VIDEO
# ==========================
class GetVideoSignedUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # '120p' | '360p' | '720p' | '1080p' | None
        quality = request.GET.get("quality")

        try:
            video = Video.objects.only(
                "id", "video_file", "converted_files"
            ).get(pk=pk)
        except Video.DoesNotExist:
            raise Http404("Video not found")

        if not video.video_file:
            raise Http404("Video file missing")

        key = self.get_key_from_model(video, quality)
        if not key:
            raise Http404("Requested quality not available")

        key = self.normalize_s3_key(key)

        if getattr(settings, "USE_S3_MEDIA", False):
            if getattr(settings, "AWS_S3_QUERYSTRING_AUTH", False) is False:
                url = self.build_public_s3_url(
                    bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    region=getattr(
                        settings, "AWS_S3_REGION_NAME", "eu-central-1"),
                    key=key,
                )
                return Response({"url": url})

            url = self.build_presigned_url(
                bucket=settings.AWS_STORAGE_BUCKET_NAME,
                region=getattr(settings, "AWS_S3_REGION_NAME", "eu-central-1"),
                key=key,
                expires=3600,  # 1 час
            )
            return Response({"url": url})

        from django.contrib.sites.shortcuts import get_current_site
        host = get_current_site(request).domain
        scheme = "https" if request.is_secure() else "http"
        media_url = settings.MEDIA_URL.rstrip("/")
        url = f"{scheme}://{host}{media_url}/{quote(key)}"
        return Response({"url": url})

    # ------- helpers -------
    def get_key_from_model(self, video: Video, quality: str | None):
        return video.get_key_for_quality(quality)

    def normalize_s3_key(self, key: str) -> str:
        key = (key or "").lstrip("/")
        key = key.replace("/.mp4", ".mp4")
        while "//" in key:
            key = key.replace("//", "/")
        return key

    def build_public_s3_url(self, bucket: str, region: str, key: str) -> str:
        safe_key = quote(key)
        return f"https://{bucket}.s3.{region}.amazonaws.com/{safe_key}"

    def build_presigned_url(self, bucket: str, region: str, key: str, expires: int = 3600) -> str:
        s3 = boto3.client("s3", region_name=region)
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ResponseContentDisposition": "inline",
                # "ResponseContentType": "video/mp4",
            },
            ExpiresIn=expires,
        )
