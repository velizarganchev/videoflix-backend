from django.db import models
import os
from moviepy import VideoFileClip
from django.core.files.base import ContentFile
from PIL import Image
import io

LIST_OF_GENRES = [
    ('Action', 'Action'),
    ('Adventure', 'Adventure'),
    ('Comedy', 'Comedy'),
    ('Crime', 'Crime'),
    ('Drama', 'Drama'),
    ('Fantasy', 'Fantasy'),
    ('Historical', 'Historical'),
    ('Horror', 'Horror'),
    ('Mystery', 'Mystery'),
    ('Philosophical', 'Philosophical'),
    ('Political', 'Political'),
    ('Romance', 'Romance'),
    ('Science fiction', 'Science fiction'),
    ('Thriller', 'Thriller'),
    ('Western', 'Western'),
    ('Animation', 'Animation'),
    ('Documentary', 'Documentary'),
    ('Biographical', 'Biographical'),
    ('Educational', 'Educational'),
    ('Erotic', 'Erotic'),
    ('Musical', 'Musical'),
    ('Reality', 'Reality'),
    ('Sports', 'Sports'),
    ('Superhero', 'Superhero'),
    ('Surreal', 'Surreal'),
    ('Other', 'Other'),
]


class Video(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(
        max_length=50, choices=LIST_OF_GENRES, blank=True, null=True)
    image_file = models.ImageField(upload_to='images', blank=True, null=True)
    video_file = models.FileField(upload_to='videos', blank=True, null=True)
    converted_files = models.JSONField(
        blank=True, null=True, default=list)

    def __str__(self):
        return f"({self.id}) {self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

    def get_converted_files(self):
        """
        Generate the paths for converted video resolutions based on the original file.
        """
        if not self.video_file:
            return []

        try:
            # Extract base path and extension
            base_path, ext = os.path.splitext(self.video_file.name)

            # Generate file paths for different resolutions
            resolutions = ["120p", "360p", "720p", "1080p"]
            converted_files = [f"{base_path}_{
                res}{ext}" for res in resolutions]

            return converted_files
        except Exception as e:
            print(f"Error generating converted file paths: {e}")
            return []

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.video_file and not self.image_file:
            self.generate_thumbnail()

    def generate_thumbnail(self):
        try:
            video_path = self.video_file.path
            thumbnail_path = f"{os.path.splitext(video_path)[0]}.jpg"

            # Extract a frame from the video
            clip = VideoFileClip(video_path)
            frame = clip.get_frame(1)  # Get a frame at 1 second

            # Convert the frame to an image
            image = Image.fromarray(frame)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            buffer.seek(0)

            # Save the image to the image_file field
            self.image_file.save(os.path.basename(
                thumbnail_path), ContentFile(buffer.read()), save=False)
            self.save()
        except Exception as e:
            print(f"Error generating thumbnail: {e}")

    class Meta:
        ordering = ['-created_at']
