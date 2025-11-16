"""
content_app.api.views — Content endpoints for Videoflix.

Provides:
- GetContentItemsView: list all videos for authenticated users (cached).
- AddFavoriteVideoView: toggle a video in the user's favorites.
- GetVideoSignedUrlView: return a streaming URL (S3 signed/public or local).
"""

from urllib.parse import quote
from django.conf import settings
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Video
from .serializers import VideoSerializer


# ==========================
# LIST
# ==========================
class GetContentItemsView(APIView):
    """
    Return a list of all Video objects, ordered by creation date (newest first).

    Access:
        - Authenticated users only.
    Caching:
        - Response is cached for a short time to reduce DB load.
    """
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(5))
    def get(self, request):
        """
        GET /api/content/

        Returns:
            - 200 OK with serialized list of videos.
        """
        qs = Video.objects.all().order_by("-created_at")
        ser = VideoSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)


# ==========================
# FAVORITES TOGGLE
# ==========================
class AddFavoriteVideoView(APIView):
    """
    Toggle a Video in the authenticated user's favorites list.

    Behavior:
        - If the video is already a favorite → remove it.
        - If not → add it.
    Returns:
        - The list of favorite video IDs for the user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/content/favorites/

        Expected payload:
            {
                "video_id": <int>
            }
        """
        user = request.user
        video_id = request.data.get("video_id")
        if not video_id:
            return Response(
                {"message": "Video ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            video = Video.objects.get(pk=video_id)
        except Video.DoesNotExist:
            return Response(
                {"message": "Video not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Toggle favorite state
        if video in user.favorite_videos.all():
            user.favorite_videos.remove(video)
        else:
            user.favorite_videos.add(video)

        ids = list(user.favorite_videos.values_list("id", flat=True))
        return Response(ids, status=status.HTTP_200_OK)


# ==========================
# SIGNED / PUBLIC / LOCAL URL
# ==========================
class GetVideoSignedUrlView(APIView):
    """
    Return a streaming URL for a video in a given quality.

    Behavior:
        - If using S3:
            * Public bucket (no querystring auth) → direct HTTPS URL.
            * Private bucket (querystring auth) → presigned URL.
        - If using local MEDIA:
            * Build an absolute URL to the media file.

    Access:
        - Authenticated users only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """
        GET /api/content/videos/<pk>/signed-url/?quality=360p

        Query params:
            - quality (optional): e.g. "120p", "360p", "720p", "1080p".
              If omitted, delegated to Video.get_key_for_quality.

        Returns:
            - 200 OK with {"url": "<string>"} on success.
            - 404 if video or requested quality is not available.
        """
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

        key = self.normalize_key(key)

        # S3 path
        if getattr(settings, "USE_S3_MEDIA", False):
            from boto3 import client as boto3_client

            # Public bucket (no querystring auth)
            if getattr(settings, "AWS_S3_QUERYSTRING_AUTH", False) is False:
                return Response(
                    {
                        "url": self.build_public_s3_url(
                            bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            region=getattr(
                                settings, "AWS_S3_REGION_NAME", "eu-central-1"
                            ),
                            key=key,
                        )
                    }
                )

            # Private → presigned URL
            s3 = boto3_client(
                "s3",
                region_name=getattr(
                    settings, "AWS_S3_REGION_NAME", "eu-central-1"
                ),
            )
            url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": key,
                    "ResponseContentDisposition": "inline",
                },
                ExpiresIn=3600,
            )
            return Response({"url": url})

        # Local MEDIA path
        host = request.get_host()
        scheme = "https" if request.is_secure() else "http"
        media_url = settings.MEDIA_URL.rstrip("/")
        url = f"{scheme}://{host}{media_url}/{quote(key)}"
        return Response({"url": url})

    # helpers
    def get_key_from_model(self, video: Video, quality: str | None):
        """
        Delegate to the Video model to resolve the storage key
        for the given quality (or default).
        """
        return video.get_key_for_quality(quality)

    def normalize_key(self, key: str) -> str:
        """
        Normalize a storage key:
        - strip leading slashes
        - fix accidental '/.mp4' patterns
        - collapse duplicate slashes
        """
        key = (key or "").lstrip("/")
        key = key.replace("/.mp4", ".mp4")
        while "//" in key:
            key = key.replace("//", "/")
        return key

    def build_public_s3_url(self, bucket: str, region: str, key: str) -> str:
        """
        Build a public HTTPS URL to an S3 object for non-signed access.
        """
        safe_key = quote(key)
        return f"https://{bucket}.s3.{region}.amazonaws.com/{safe_key}"
