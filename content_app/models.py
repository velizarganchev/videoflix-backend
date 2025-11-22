"""
content_app.models — Video model for Videoflix backend.

Local:   FILE (MEDIA_ROOT / MEDIA_URL)
Prod:    S3 (USE_S3_MEDIA=True)

- Thumbnail is generated asynchronously via RQ (see tasks.generate_thumbnail_task).
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models

# -----------------------------
# Storage selection (S3 vs Local)
# -----------------------------
if getattr(settings, "USE_S3_MEDIA", False):
    try:
        from storages.backends.s3boto3 import S3Boto3Storage  # type: ignore
        media_storage = S3Boto3Storage()
    except Exception:
        media_storage = FileSystemStorage(
            location=settings.MEDIA_ROOT,
            base_url=settings.MEDIA_URL,
        )
else:
    media_storage = FileSystemStorage(
        location=settings.MEDIA_ROOT,
        base_url=settings.MEDIA_URL,
    )


LIST_OF_GENRES = [
    ("Action", "Action"),
    ("Adventure", "Adventure"),
    ("Comedy", "Comedy"),
    ("Crime", "Crime"),
    ("Drama", "Drama"),
    ("Fantasy", "Fantasy"),
    ("Historical", "Historical"),
    ("Horror", "Horror"),
    ("Mystery", "Mystery"),
    ("Philosophical", "Philosophical"),
    ("Political", "Political"),
    ("Romance", "Romance"),
    ("Science fiction", "Science fiction"),
    ("Thriller", "Thriller"),
    ("Western", "Western"),
    ("Animation", "Animation"),
    ("Documentary", "Documentary"),
    ("Biographical", "Biographical"),
    ("Educational", "Educational"),
    ("Erotic", "Erotic"),
    ("Musical", "Musical"),
    ("Reality", "Reality"),
    ("Sports", "Sports"),
    ("Superhero", "Superhero"),
    ("Surreal", "Surreal"),
    ("Other", "Other"),
]


def validate_video_file_size(value):
    """
    Ensure uploaded video file is not larger than the allowed limit (200 MB).
    If exceeded, raise ValidationError so Django admin shows a clear message.
    """
    limit_mb = 200
    limit_bytes = limit_mb * 1024 * 1024

    if value.size > limit_bytes:
        raise ValidationError(
            f"Video file is too large. Maximum allowed size is {limit_mb} MB."
        )


class Video(models.Model):
    VIDEOS_SUBDIR = "videos"
    IMAGES_SUBDIR = "images"
    QUALITIES = ("120p", "360p", "720p", "1080p")

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"

    PROCESSING_STATES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED, "Failed"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)

    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    category = models.CharField(
        max_length=50,
        choices=LIST_OF_GENRES,
        blank=True,
        null=True,
    )

    processing_state = models.CharField(
        max_length=16,
        choices=PROCESSING_STATES,
        default=STATUS_PENDING,
        help_text="Background processing state.",
    )

    processing_error = models.TextField(
        blank=True,
        null=True,
        help_text="Last processing error message, if any.",
    )

    video_file = models.FileField(
        storage=media_storage,
        upload_to=f"{VIDEOS_SUBDIR}/",
        validators=[validate_video_file_size],
    )

    image_file = models.ImageField(
        storage=media_storage,
        upload_to=f"{IMAGES_SUBDIR}/",
        blank=True,
        null=True,
        editable=False,
    )

    converted_files = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        editable=False,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        ts = self.created_at.strftime(
            "%Y-%m-%d %H:%M:%S") if self.created_at else "—"
        return f"({self.id}) {self.title} ({ts})"

    # ---------- helpers ----------

    def _base_path_and_ext_from_name(self, name: str) -> Tuple[str | None, str | None]:
        if not name:
            return None, None
        base_path, ext = os.path.splitext(name)
        return base_path, ext

    def _build_converted_map_from_name(self, final_name: str | None) -> Dict[str, str]:
        """
        Build mapping for all QUALITIES based on final storage name.
        Result example:
            {"360p": "videos/myvideo_360p.mp4", ...}
        """
        if not final_name:
            return {}
        base, ext = self._base_path_and_ext_from_name(final_name)
        if not base:
            return {}
        return {q: f"{base}_{q}{ext}" for q in self.QUALITIES}

    def get_key_for_quality(self, quality: str | None = None) -> str | None:
        """Return correct storage key depending on quality."""
        if not self.video_file:
            return None
        if not quality:
            return self.video_file.name
        if isinstance(self.converted_files, dict) and quality in self.converted_files:
            return self.converted_files[quality]
        return self._build_converted_map_from_name(self.video_file.name).get(quality)

    def save(self, *args, **kwargs) -> None:
        """
        Ensure that `converted_files` is always in sync with the latest filename.
        Does not validate or block creation (admin handles that).
        """
        super().save(*args, **kwargs)

        final_name = self.video_file.name if self.video_file else None
        correct_map = self._build_converted_map_from_name(final_name)
        current_map = self.converted_files or {}

        if correct_map and correct_map != current_map:
            self.converted_files = correct_map
            super().save(update_fields=["converted_files"])
