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

# регион от settings (по-надеждно е от глобалния профил)
_s3_region = getattr(settings, "AWS_S3_REGION_NAME", "eu-central-1")
s3 = boto3.client("s3", region_name=_s3_region)


def _download(bucket: str, key: str) -> str:
    fd, tmp_path = tempfile.mkstemp(suffix=os.path.splitext(key)[1])
    os.close(fd)
    s3.download_file(bucket, key, tmp_path)
    return tmp_path


def _upload(bucket: str, key: str, local_path: str, public: bool):
    extra = {
        "ContentType": mimetypes.guess_type(key)[0] or "application/octet-stream",
        "CacheControl": "public, max-age=31536000, immutable",
    }

    # Ако bucket блокира публични ACL, пробваме без ACL като fallback
    try:
        if public:
            s3.upload_file(local_path, bucket, key, ExtraArgs={
                           **extra, "ACL": "public-read"})
        else:
            s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if public and code in ("InvalidRequest", "AccessDenied"):
            # fallback без ACL
            logger.warning(
                "Upload with ACL failed (%s). Retrying without ACL for %s", code, key)
            s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
        else:
            raise


def _is_public():
    # публични URL-и, когато AWS_S3_QUERYSTRING_AUTH=False
    return getattr(settings, "AWS_S3_QUERYSTRING_AUTH", False) is False


def _ffmpeg(src: str, dst: str, height: int):
    # -2 за ширина поддържа мод 2, добра съвместимост за H.264
    cmd = (
        f"ffmpeg -y -i {shlex.quote(src)} -vf scale=-2:{height} "
        f"-c:v libx264 -preset veryfast -crf 28 -c:a aac -movflags +faststart {shlex.quote(dst)}"
    )
    subprocess.run(cmd, shell=True, check=True)


def _convert(bucket: str, src_key: str, height: int, suffix: str):
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
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 120, "120p")


def convert_to_360p(src_key):
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 360, "360p")


def convert_to_720p(src_key):
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 720, "720p")


def convert_to_1080p(src_key):
    return _convert(settings.AWS_STORAGE_BUCKET_NAME, src_key, 1080, "1080p")


def remove_file_task(key: str):
    try:
        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
    except Exception as e:
        logger.error("S3 delete failed for %s: %s", key, e)


def delete_original_video_task(key: str):
    remove_file_task(key)
