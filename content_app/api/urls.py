"""
content_app.urls — API routes for Videoflix content module

Defines all endpoints related to video content management.

Includes:
- Listing all videos
- Retrieving a single video
- Adding a video to user favorites
- Fetching signed video URLs for secure streaming access
"""

from django.urls import path
from .views import (
    GetContentItemsView,
    GetSingleContentItemView,
    AddFavoriteVideoView,
    GetVideoSignedUrlView,
)

# ----------------------------------------------------------------------
# Content API Endpoints
# ----------------------------------------------------------------------
urlpatterns = [
    # --- Video listing and retrieval ---
    path("", GetContentItemsView.as_view(), name="content"),
    path("<int:pk>/", GetSingleContentItemView.as_view(), name="content-item"),

    # --- Favorites and signed URLs ---
    path("add-favorite/", AddFavoriteVideoView.as_view(), name="add-favorite"),
    path("video-url/<int:pk>/", GetVideoSignedUrlView.as_view(), name="video-url"),
]
