"""
content_app.admin — Django admin registration for Videoflix content module

Purpose:
--------
Registers the Video model in the Django Admin interface,
allowing superusers to view, edit, and manage video entries.
"""

from django.contrib import admin
from .models import Video

# Register the Video model for admin management
admin.site.register(Video)
