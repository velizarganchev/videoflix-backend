"""
Video processing tasks for Videoflix.

This module provides:
- ffmpeg helpers for video transcoding and thumbnail extraction
- local filesystem helpers (MEDIA_ROOT)
- S3 helpers for upload/download/remove
- unified convert/remove API used by RQ workers
- a thumbnail task that updates Video.image_file
"""

from __future__ import annotations

import os
import tempfile
import logging
import subprocess
import mimetypes
import shutil

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# Flag that controls whether media is stored on S3 or locally
USE_S3 = bool(getattr(settings, "USE_S3_MEDIA", False))
S3_REGION = getattr(settings, "AWS_S3_REGION_NAME", "eu-central-1")


# ----------------------------
# S3 client
# ----------------------------
def _s3():
    """
    Return a low-level S3 client configured for the project region.
    """
    return boto3.client("s3", region_name=S3_REGION)


# ----------------------------
# ffmpeg helpers
# ----------------------------
def _ffmpeg(src: str, dst: str, height: int) -> None:
    """
    Transcode 'src' to H.264/AAC 'dst' with target height and +faststart.
    """
    args = [
        "ffmpeg",
        "-y",
        "-i",
        src,
        "-vf",
        f"scale=-2:{height}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        dst,
    ]
    subprocess.run(args, check=True)


def _ffmpeg_thumbnail(src: str, dst: str, time_sec: float = 1.0) -> None:
    """
    Extract a single JPEG frame from the video at the given time.
    """
    args = [
        "ffmpeg",
        "-y",
        "-ss",
        str(time_sec),
        "-i",
        src,
        "-vframes",
        "1",
        "-q:v",
        "2",
        dst,
    ]
    subprocess.run(args, check=True)


# ----------------------------
# Local helpers (USE_S3 = False)
# ----------------------------
def _local_src_path(key: str) -> str:
    """
    Build an absolute path under MEDIA_ROOT for the given storage key.
    """
    return os.path.join(settings.MEDIA_ROOT, key.replace("/", os.sep))


def _local_dst_path(dst_key: str) -> str:
    """
    Ensure the destination directory exists and return the absolute path.
    """
    abs_path = _local_src_path(dst_key)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return abs_path


def _local_convert(src_key: str, height: int, suffix: str) -> str:
    """
    Convert a MEDIA_ROOT video to a rendition and place it back under MEDIA_ROOT.

    Returns:
        The destination key (relative to MEDIA_ROOT).
    """
    src_abs = _local_src_path(src_key)
    if not os.path.exists(src_abs):
        raise FileNotFoundError(src_abs)

    base, ext = os.path.splitext(src_key)
    dst_key = f"{base}_{suffix}{ext}"
    dst_abs = _local_dst_path(dst_key)

    fd, tmp_dst = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        _ffmpeg(src_abs, tmp_dst, height)
        shutil.move(tmp_dst, dst_abs)
    finally:
        try:
            if os.path.exists(tmp_dst):
                os.remove(tmp_dst)
        except Exception:
            pass

    return dst_key


def _local_remove(key: str) -> None:
    """
    Delete a MEDIA_ROOT file if it exists.
    """
    abs_path = _local_src_path(key)
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception as e:
        logger.warning("Local delete failed for %s: %s", abs_path, e)


# ----------------------------
# S3 helpers (USE_S3 = True)
# ----------------------------
def _s3_download(bucket: str, key: str) -> str:
    """
    Download an S3 object to a temporary local file and return its path.
    """
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key)[1])
    os.close(fd)
    _s3().download_file(bucket, key, tmp_path)
    return tmp_path


def _s3_upload(bucket: str, key: str, local_path: str, public: bool) -> None:
    """
    Upload a local file to S3 with basic content-type and cache headers.

    If 'public' is True, it tries to set ACL public-read and falls back
    to a private upload when ACLs are blocked.
    """
    extra = {
        "ContentType": mimetypes.guess_type(key)[0] or "application/octet-stream",
        "CacheControl": "public, max-age=31536000, immutable",
    }
    try:
        if public:
            _s3().upload_file(
                local_path,
                bucket,
                key,
                ExtraArgs={**extra, "ACL": "public-read"},
            )
        else:
            _s3().upload_file(local_path, bucket, key, ExtraArgs=extra)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if public and code in ("InvalidRequest", "AccessDenied"):
            logger.warning(
                "ACL upload blocked (%s), retrying without ACL for %s", code, key
            )
            _s3().upload_file(local_path, bucket, key, ExtraArgs=extra)
        else:
            raise


def _is_public() -> bool:
    """
    Return True when S3 objects should be publicly accessible by URL.

    This is based on AWS_S3_QUERYSTRING_AUTH being disabled.
    """
    return getattr(settings, "AWS_S3_QUERYSTRING_AUTH", False) is False


def _s3_convert(src_key: str, height: int, suffix: str) -> str:
    """
    Convert a video stored on S3 and upload the rendition back to S3.

    Returns:
        The destination key on S3.
    """
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    local_src = _s3_download(bucket, src_key)

    base, ext = os.path.splitext(src_key)
    dst_key = f"{base}_{suffix}{ext}"

    fd, local_dst = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        _ffmpeg(local_src, local_dst, height)
        _s3_upload(bucket, dst_key, local_dst, _is_public())
        return dst_key
    finally:
        for p in (local_src, local_dst):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def _s3_remove(key: str) -> None:
    """
    Delete an object from S3, logging any failure.
    """
    try:
        _s3().delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
    except Exception as e:
        logger.error("S3 delete failed for %s: %s", key, e)


# ----------------------------
# Unified API (convert/remove)
# ----------------------------
def _convert_generic(src_key: str, height: int, suffix: str) -> str:
    """
    Convert a video to target height.

    Branches to S3 or local backend based on USE_S3
    and returns the destination key.
    """
    if USE_S3:
        return _s3_convert(src_key, height, suffix)
    return _local_convert(src_key, height, suffix)


def convert_to_120p(src_key: str) -> str:
    """
    RQ-friendly task wrapper to convert a video to 120p.
    """
    return _convert_generic(src_key, 120, "120p")


def convert_to_360p(src_key: str) -> str:
    """
    RQ-friendly task wrapper to convert a video to 360p.
    """
    return _convert_generic(src_key, 360, "360p")


def convert_to_720p(src_key: str) -> str:
    """
    RQ-friendly task wrapper to convert a video to 720p.
    """
    return _convert_generic(src_key, 720, "720p")


def convert_to_1080p(src_key: str) -> str:
    """
    RQ-friendly task wrapper to convert a video to 1080p.
    """
    return _convert_generic(src_key, 1080, "1080p")


def remove_file_task(key: str) -> None:
    """
    Delete an original or rendition (local or S3) via a unified API.
    """
    if USE_S3:
        _s3_remove(key)
    else:
        _local_remove(key)


def delete_original_video_task(key: str) -> None:
    """
    Backwards-compatible alias for remove_file_task.
    """
    remove_file_task(key)


# ----------------------------
# Thumbnail task
# ----------------------------
def generate_thumbnail_task(src_key: str, time_sec: float = 1.0) -> None:
    """
    Generate a JPG thumbnail for the given video key and attach it to
    the corresponding Video.image_file.

    Works for both local MEDIA_ROOT and S3-backed storage.

    Also updates Video.processing_state:
    - "ready"  on success
    - "failed" on error
    """
    from .models import Video  # lazy import to avoid circular imports

    video = Video.objects.filter(video_file=src_key).first()
    if not video:
        logger.warning(
            "No Video found for key %s when generating thumbnail", src_key
        )
        return

    if video.image_file:
        return

    base_name = os.path.splitext(os.path.basename(src_key))[0]
    thumb_filename = f"{base_name}.jpg"
    thumb_key = f"{Video.IMAGES_SUBDIR}/{thumb_filename}"

    cleanup_paths: list[str] = []

    try:
        if USE_S3:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            src_path = _s3_download(bucket, src_key)
            cleanup_paths.append(src_path)
        else:
            src_path = _local_src_path(src_key)
            if not os.path.exists(src_path):
                logger.warning(
                    "Source video not found for thumbnail: %s", src_path
                )
                return

        fd, tmp_thumb = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        cleanup_paths.append(tmp_thumb)

        _ffmpeg_thumbnail(src_path, tmp_thumb, time_sec=time_sec)

        if USE_S3:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            _s3_upload(bucket, thumb_key, tmp_thumb, _is_public())
        else:
            dst_abs = _local_dst_path(thumb_key)
            shutil.move(tmp_thumb, dst_abs)

        # Update Video model:
        # - point to the thumbnail
        # - mark processing as READY and clear any previous error
        video.image_file.name = thumb_key
        video.processing_state = Video.STATUS_READY
        video.processing_error = ""
        video.save(update_fields=["image_file",
                   "processing_state", "processing_error"])

    except Exception as exc:
        logger.exception("Thumbnail generation failed for %s", src_key)
        try:
            # Mark processing as FAILED and store a short error message
            video.processing_state = Video.STATUS_FAILED
            video.processing_error = f"Thumbnail generation failed: {exc}"
            video.save(update_fields=["processing_state", "processing_error"])
        except Exception:
            # Avoid cascading failures
            logger.exception(
                "Could not update processing_state for %s", src_key)
    finally:
        # Cleanup temporary files if they still exist
        for p in cleanup_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
