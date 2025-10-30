"""
videoflix_backend_app.urls

Main URL configuration for the Videoflix backend.

This file defines all top-level URL routes, including:
- Home & health endpoints
- Admin panel
- Django RQ dashboard
- API routes (users_app, content_app)
- Static and media file serving during development
- Debug toolbar (only active when DEBUG=True)
"""

import debug_toolbar
from django.shortcuts import render
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views


# ----------------------------------------------------------------------
# 1. Root and simple views
# ----------------------------------------------------------------------
def home(request):
    """Simple homepage view (can later be replaced by a landing page)."""
    return render(request, "home.html")


# ----------------------------------------------------------------------
# 2. Core URL patterns
# ----------------------------------------------------------------------
urlpatterns = [
    path("", home, name="home"),
    # basic health endpoint
    path("health/", views.health_check, name="health-check"),
    path("admin/", admin.site.urls),                          # Django admin
    path("django-rq/", include("django_rq.urls")
         ),             # Redis Queue dashboard
    path("users/", include("users_app.api.urls")
         ),             # User management APIs
    # Video/content APIs
    path("content/", include("content_app.api.urls")),
]

# ----------------------------------------------------------------------
# 3. Development mode: serve static/media & enable debug toolbar
# ----------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
