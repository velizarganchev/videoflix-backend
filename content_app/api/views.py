"""
content_app.api.views — Content endpoints for Videoflix

Provides:
- Listing all videos (short-lived cached)
- Retrieving a single video
- Toggling user's favorite videos
- Generating signed/public URLs for video streaming (S3 or local media)

Notes:
- The list endpoint uses a short cache (10s) to reduce DB/ORM load while keeping content fresh.
- Signed URL generation uses boto3 when USE_S3_MEDIA=True.
- For public S3 (no querystring auth), direct object URL is returned.
- For local media, builds absolute URL from current site + MEDIA_URL.
"""

from django.conf import settings
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from urllib.parse import quote
import boto3

from ..models import Video
from .serializers import VideoSerializer


# ==========================
# LIST + DETAIL
# ==========================
class GetContentItemsView(APIView):
    """
    Return the full list of videos.

    Caching:
        Response is cached for 10 seconds via cache_page decorator.
        This provides a balance between performance and freshness.
    """
    permission_classes = [IsAuthenticated]

    @method_decorator(cache_page(10))  # short-lived cache: 10 seconds
    def get(self, request):
        """List all Video objects (newest first)."""
        qs = Video.objects.all().order_by('-created_at')
        ser = VideoSerializer(qs, many=True)
        return Response(ser.data)

# ==========================
# FAVORITES TOGGLE
# ==========================


class AddFavoriteVideoView(APIView):
    """
    Toggle a video in the authenticated user's favorites.

    Expects:
        POST body with "video_id".
    Returns:
        List of favorite video IDs for the current user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Add or remove the given video from user's favorites."""
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
    """
    Build a playable URL for a video (by quality), either:
    - S3 public object URL (if AWS_S3_QUERYSTRING_AUTH=False),
    - S3 presigned URL (if AWS_S3_QUERYSTRING_AUTH=True),
    - or local MEDIA URL when not using S3.

    Expects:
        Query param "quality" in {"120p","360p","720p","1080p"} or omitted/None.

    Raises:
        Http404: if video/quality/key not present.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """Return a JSON object with {"url": "<resolved video URL>"}."""
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

        # S3 media path
        if getattr(settings, "USE_S3_MEDIA", False):
            # Public bucket (no querystring auth) → static URL
            if getattr(settings, "AWS_S3_QUERYSTRING_AUTH", False) is False:
                url = self.build_public_s3_url(
                    bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    region=getattr(
                        settings, "AWS_S3_REGION_NAME", "eu-central-1"),
                    key=key,
                )
                return Response({"url": url})

            # Private bucket → presigned URL with expiry
            url = self.build_presigned_url(
                bucket=settings.AWS_STORAGE_BUCKET_NAME,
                region=getattr(settings, "AWS_S3_REGION_NAME", "eu-central-1"),
                key=key,
                expires=3600,  # 1 hour
            )
            return Response({"url": url})

        # Local media fallback (non-S3)
        from django.contrib.sites.shortcuts import get_current_site
        host = get_current_site(request).domain
        scheme = "https" if request.is_secure() else "http"
        media_url = settings.MEDIA_URL.rstrip("/")
        url = f"{scheme}://{host}{media_url}/{quote(key)}"
        return Response({"url": url})

    # ------- helpers -------
    def get_key_from_model(self, video: Video, quality: str | None):
        """
        Return storage key for requested quality using model helper.

        Delegates to: Video.get_key_for_quality(quality)
        """
        return video.get_key_for_quality(quality)

    def normalize_s3_key(self, key: str) -> str:
        """
        Normalize a storage key:
        - remove leading slash,
        - fix accidental '/.mp4' to '.mp4',
        - collapse double slashes.
        """
        key = (key or "").lstrip("/")
        key = key.replace("/.mp4", ".mp4")
        while "//" in key:
            key = key.replace("//", "/")
        return key

    def build_public_s3_url(self, bucket: str, region: str, key: str) -> str:
        """Return direct public S3 object URL (no querystring)."""
        safe_key = quote(key)
        return f"https://{bucket}.s3.{region}.amazonaws.com/{safe_key}"

    def build_presigned_url(self, bucket: str, region: str, key: str, expires: int = 3600) -> str:
        """Generate an expiring S3 presigned URL for the given object key."""
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
