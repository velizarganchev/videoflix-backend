"""
content_app.urls — API routes for Videoflix content module

Defines all endpoints related to video content management.

Includes:
- Listing all videos
- Adding a video to user favorites
- Fetching signed video URLs for secure streaming access
"""

from django.urls import path
from .views import (
    GetContentItemsView,
    AddFavoriteVideoView,
    GetVideoSignedUrlView,
)

# ----------------------------------------------------------------------
# Content API Endpoints
# ----------------------------------------------------------------------
urlpatterns = [
    # --- Video listing and retrieval ---
    path("", GetContentItemsView.as_view(), name="content"),

    # --- Favorites and signed URLs ---
    path("add-favorite/", AddFavoriteVideoView.as_view(), name="add-favorite"),
    path("video-url/<int:pk>/", GetVideoSignedUrlView.as_view(), name="video-url"),
]
