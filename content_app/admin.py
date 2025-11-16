"""
content_app.admin — Django admin registration for Videoflix content module

Purpose:
--------
Registers the Video model in the Django Admin interface,
allowing superusers to view, edit, and manage video entries.
"""

from django.contrib import admin
from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at", "id")
    fields = (
        "title",
        "description",
        "category",
        "video_file",
        "image_file",
        "converted_files",
        "created_at",
    )

    readonly_fields = (
        "image_file",
        "converted_files",
        "created_at",
    )
