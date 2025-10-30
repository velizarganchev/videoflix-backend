"""
content_app.tasks — Background tasks for Videoflix content processing

Purpose:
--------
- Download/upload media to S3
- Transcode videos to multiple resolutions via FFmpeg
- Delete source/rendition objects from S3

Notes:
- Uses boto3 client configured with region from settings.AWS_S3_REGION_NAME.
- Public vs presigned serving is inferred from AWS_S3_QUERYSTRING_AUTH.
- No functional changes: documentation and clarity only.
"""

# content_app/tasks.py
import os
import shlex
import tempfile
import logging
import subprocess
import mimetypes

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# Region from settings (more reliable than relying on global AWS profile)
_s3_region = getattr(settings, "AWS_S3_REGION_NAME", "eu-central-1")
s3 = boto3.client("s3", region_name=_s3_region)


def _download(bucket: str, key: str) -> str:
    """
    Download an S3 object to a temporary local file.

    Args:
        bucket (str): S3 bucket name.
        key (str): Object key in S3.

    Returns:
        str: Path to the temporary local file.
    """
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key)[1])
    os.close(fd)
    s3.download_file(bucket, key, tmp_path)
    return tmp_path


def _upload(bucket: str, key: str, local_path: str, public: bool):
    """
    Upload a local file to S3 with sensible defaults for media.

    Sets:
        - ContentType based on filename
        - CacheControl for long-lived immutable assets

    If `public=True`, attempts to set ACL public-read. If the bucket blocks
    ACLs, retries upload without ACL to avoid failure.
    """
    extra = {
        "ContentType": mimetypes.guess_type(key)[0] or "application/octet-stream",
        "CacheControl": "public, max-age=31536000, immutable",
    }

    try:
        if public:
            s3.upload_file(local_path, bucket, key, ExtraArgs={
                           **extra, "ACL": "public-read"})
        else:
            s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if public and code in ("InvalidRequest", "AccessDenied"):
            # Fallback: bucket enforces "ACLs disabled" — retry without ACL
            logger.warning(
                "Upload with ACL failed (%s). Retrying without ACL for %s", code, key)
            s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
        else:
            raise


def _is_public():
    """
    Decide whether objects should be publicly accessible via static URLs.

    Returns:
        bool: True when AWS_S3_QUERYSTRING_AUTH is False (public objects),
              False when presigned URLs are preferred.
    """
    # Public URLs when querystring auth is disabled
    return getattr(settings, "AWS_S3_QUERYSTRING_AUTH", False) is False


def _ffmpeg(src: str, dst: str, height: int):
    """
    Transcode a source video to H.264/AAC at a target height with faststart.

    Command notes:
        - scale=-2:{height} keeps width even (mod 2) for H.264 compatibility
        - libx264 veryfast + crf=28 is a reasonable size/quality trade-off
        - aac audio codec; +faststart moves moov atom to the beginning
    """
    cmd = (
        f"ffmpeg -y -i {shlex.quote(src)} -vf scale=-2:{height} "
        f"-c:v libx264 -preset veryfast -crf 28 -c:a aac -movflags +faststart {shlex.quote(dst)}"
    )
    subprocess.run(cmd, shell=True, check=True)


def _convert(bucket: str, src_key: str, height: int, suffix: str):
    """
    Helper to download a source object, transcode it, and upload the rendition.

    Args:
        bucket (str): S3 bucket name.
        src_key (str): Source object key.
        height (int): Target vertical resolution (e.g., 360, 720).
        suffix (str): Suffix label for the rendition key (e.g., "360p").

    Returns:
        str: Destination key uploaded to S3.

    Always removes temporary files on exit.
    """
    local_src = _download(bucket, src_key)
    base, ext = os.path.splitext(src_key)
    dst_key = f"{base}_{suffix}{ext}"
    fd, local_dst = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        _ffmpeg(local_src, local_dst, height)
        _upload(bucket, dst_key, local_dst, _is_public())
        return dst_key
    finally:
        for p in (local_src, local_dst):
            try:
                os.remove(p)
            except Exception:
                pass


def convert_to_120p(src_key):
    """Enqueueable task: transcode to 120p and upload to S3. Returns dst key."""
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 120, "120p")


def convert_to_360p(src_key):
    """Enqueueable task: transcode to 360p and upload to S3. Returns dst key."""
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 360, "360p")


def convert_to_720p(src_key):
    """Enqueueable task: transcode to 720p and upload to S3. Returns dst key."""
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 720, "720p")


def convert_to_1080p(src_key):
    """Enqueueable task: transcode to 1080p and upload to S3. Returns dst key."""
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 1080, "1080p")


def remove_file_task(key: str):
    """
    Enqueueable task: delete an object from S3.

    Args:
        key (str): S3 object key to delete.
    """
    try:
        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
    except Exception as e:
        logger.error("S3 delete failed for %s: %s", key, e)


def delete_original_video_task(key: str):
    """
    Enqueueable task: delete the original uploaded video object.

    Typically used after renditions are generated and verified.
    """
    remove_file_task(key)
