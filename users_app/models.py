"""
users_app.models — Custom UserProfile model for Videoflix backend

Extends Django's AbstractUser with additional fields
for user contact information and personalized content preferences.

Includes:
- phone: optional contact number
- address: optional user address
- favorite_videos: many-to-many relation with Video model
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from content_app.models import Video


class UserProfile(AbstractUser):
    """
    Custom user model extending Django’s AbstractUser.

    Adds:
        phone (CharField): Optional phone number.
        address (TextField): Optional user address (max length 120).
        favorite_videos (ManyToManyField): Related videos the user has liked or saved.
    """

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Optional phone number for the user.",
    )
    address = models.TextField(
        max_length=120,
        blank=True,
        null=True,
        help_text="Optional address for the user (up to 120 characters).",
    )
    favorite_videos = models.ManyToManyField(
        Video,
        related_name="users",
        blank=True,
        help_text="Videos marked as favorites by the user.",
    )
