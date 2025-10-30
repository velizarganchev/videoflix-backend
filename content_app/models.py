"""
content_app.models — Video model for Videoflix backend

Purpose:
--------
Defines the Video model representing uploaded video content,
including metadata, storage references (S3 or local), and helper
methods for generating thumbnails and quality-specific keys.

Features:
- Supports S3 and local file storage backends
- Automatically generates thumbnail on creation (if MoviePy is available)
- Provides helper methods for handling video quality mapping
"""

from django.db import models
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
import os
import io
import tempfile

# Attempt to import lightweight video processing library (optional)
try:
    from moviepy import VideoFileClip
except Exception:
    VideoFileClip = None  # Safe fallback if MoviePy is not installed

# --- Force S3 storage for video/image fields if available ---
try:
    from storages.backends.s3boto3 import S3Boto3Storage
    s3_storage = S3Boto3Storage()
except Exception:
    # Fallback to local storage if django-storages is missing
    from django.core.files.storage import FileSystemStorage
    s3_storage = FileSystemStorage()

# --- Genre choices ---
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


class Video(models.Model):
    """
    Represents a video object in the Videoflix platform.

    Fields:
        created_at (DateTime): Auto-set creation timestamp.
        title (CharField): Unique video title.
        description (TextField): Description of the video.
        category (CharField): Optional genre/category.
        image_file (ImageField): Thumbnail or preview image.
        video_file (FileField): Original uploaded video file.
        converted_files (JSONField): Map of quality resolutions to file keys.

    Behavior:
        - On save, automatically builds converted_files mapping.
        - On creation, auto-generates thumbnail if MoviePy is available.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(
        max_length=50, choices=LIST_OF_GENRES, blank=True, null=True
    )

    # Force S3 (or fallback storage)
    image_file = models.ImageField(
        storage=s3_storage, upload_to="images", blank=True, null=True
    )
    video_file = models.FileField(
        storage=s3_storage, upload_to="videos", blank=True, null=True
    )

    # Stores resolution map, e.g. { "360p": "videos/..._360p.mp4", ... }
    converted_files = models.JSONField(blank=True, null=True, default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        """Readable string representation for admin and debugging."""
        return f"({self.id}) {self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

    # ---- S3 key helpers ----
    QUALITIES = ("120p", "360p", "720p", "1080p")

    def base_path_and_ext(self):
        """
        Return (base_path, ext) from the original video file name.
        Example:
            'videos/123/video.mp4' -> ('videos/123/video', '.mp4')
        """
        if not self.video_file:
            return None, None
        base_path, ext = os.path.splitext(self.video_file.name)
        return base_path, ext

    def build_converted_map(self):
        """
        Build a dictionary mapping available quality keys to file paths.

        Does not upload or create files; only generates predictable filenames.
        """
        base, ext = self.base_path_and_ext()
        if not base:
            return {}
        return {q: f"{base}_{q}{ext}" for q in self.QUALITIES}

    def get_key_for_quality(self, quality: str | None = None):
        """
        Return the storage key for a given video quality.

        If quality is None:
            Returns the original file key (self.video_file.name)
        If converted_files dict exists in DB:
            Uses stored mapping.
        Otherwise:
            Dynamically builds the key from the base path.
        """
        if not self.video_file:
            return None

        if not quality:
            return self.video_file.name

        if isinstance(self.converted_files, dict) and quality in self.converted_files:
            return self.converted_files[quality]

        base, ext = self.base_path_and_ext()
        if not base:
            return None
        return f"{base}_{quality}{ext}"

    # ---- Thumbnail generation ----
    def save(self, *args, **kwargs):
        """
        Override save() to:
        1) Normalize converted_files to a dict.
        2) On CREATE (no pk yet), if video_file exists but no image_file:
            - Write upload stream to a temporary local file.
            - Generate a thumbnail at 1.0s using MoviePy.
            - Upload it to image_file (S3 or default storage).
        3) Always reset file pointer to ensure proper upload.
        """
        # Normalize converted_files to dict if needed
        if not self.converted_files or isinstance(self.converted_files, list):
            self.converted_files = self.build_converted_map()

        creating = self.pk is None
        need_thumb = creating and self.video_file and not self.image_file

        tmp_path = None
        if need_thumb:
            try:
                # Get file-like object from upload
                fileobj = self.video_file

                # Create a temporary local copy of the uploaded file
                suffix = os.path.splitext(getattr(fileobj, "name", "video.mp4"))[
                    1] or ".mp4"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                with os.fdopen(fd, "wb") as tmpf:
                    if hasattr(fileobj, "chunks"):
                        for chunk in fileobj.chunks():
                            tmpf.write(chunk)
                    else:
                        tmpf.write(fileobj.read())

                # Generate thumbnail if MoviePy is available
                if VideoFileClip:
                    self._generate_thumbnail_local(tmp_path, time_sec=1.0)

                # Reset file pointer after reading stream (important for storage upload)
                try:
                    fileobj.seek(0)
                except Exception:
                    pass

            except Exception as e:
                # Do not interrupt save process if thumbnail generation fails
                print(f"Thumbnail generation skipped: {e}")
            finally:
                # Clean up temporary file
                if tmp_path:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        # Perform standard save
        super().save(*args, **kwargs)

    def _generate_thumbnail_local(self, video_path: str, time_sec: float = 1.0):
        """
        Generate a thumbnail from a local video file and upload it to image_file.

        Works seamlessly with S3 or local storage, since image_file.save()
        automatically uses its configured backend.
        """
        try:
            base_name = os.path.splitext(
                os.path.basename(self.video_file.name))[0]
            thumb_name = f"{base_name}.jpg"

            clip = VideoFileClip(video_path)
            frame = clip.get_frame(time_sec)
            image = Image.fromarray(frame)

            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            buf.seek(0)

            # Save thumbnail to the configured storage (S3 or local)
            self.image_file.save(
                thumb_name,
                ContentFile(buf.read()),
                save=False,  # Prevent recursive save()
            )
        except Exception as e:
            print(f"Thumbnail generation failed: {e}")
