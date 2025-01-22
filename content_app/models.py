from django.db import models
import os

# List of genres
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
        max_length=50, choices=LIST_OF_GENRES, blank=True, null=True)  # Fixed field definition
    image_file = models.ImageField(upload_to='images', blank=True, null=True)
    video_file = models.FileField(upload_to='videos', blank=True, null=True)
    converted_files = models.JSONField(
        blank=True, null=True, default=list)  # Default to an empty list

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

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

    class Meta:
        # Order videos by creation date (newest first)
        ordering = ['-created_at']
