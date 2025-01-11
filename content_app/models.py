from django.db import models

# Create your models here.

class Video(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    image_file = models.ImageField(upload_to='images', blank=True, null=True)
    video_file = models.FileField(upload_to='videos', blank=True, null=True)
    converted_files = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title