from django.db import models
import os
from django.db.models import JSONField


class Video(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    image_file = models.ImageField(upload_to='images', blank=True, null=True)
    video_file = models.FileField(upload_to='videos', blank=True, null=True)
    converted_files = JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

    def get_converted_files(self):
        try:
            if not self.video_file or not os.path.isfile(self.video_file.path):
                return []
            base_path, ext = os.path.splitext(self.video_file.url)
            return [
                f"{base_path}_120p{ext}",
                f"{base_path}_360p{ext}",
                f"{base_path}_720p{ext}",
                f"{base_path}_1080p{ext}",
            ]
        except Exception as e:
            print(f"Error generating converted file paths: {e}")
            return []
