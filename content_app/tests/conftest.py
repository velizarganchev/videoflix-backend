from content_app.models import Video
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.conf import settings
import django
import os
import pytest

# -----------------------------------------------------------------------------------
# EARLY DJANGO SETUP: enforce LocMem cache before middleware or django_redis loads
# -----------------------------------------------------------------------------------
os.environ["USE_SQLITE_LOCAL"] = "1"
os.environ["DJANGO_SETTINGS_MODULE"] = "videoflix_backend_app.settings"


django.setup()

# Replace Redis-based cache with in-memory cache immediately
settings.CACHES["default"] = {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "videoflix-test-cache",
}
settings.CACHES["pages"] = settings.CACHES["default"]

# -----------------------------------------------------------------------------------
# IMPORTS after setup
# -----------------------------------------------------------------------------------


# -----------------------------------------------------------------------------------
# DRF API clients (authenticated & unauthenticated)
# -----------------------------------------------------------------------------------
@pytest.fixture
def api():
    """Unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Simple test user for authentication."""
    User = get_user_model()
    return User.objects.create_user(
        username="tester@example.com",
        email="tester@example.com",
        password="pass1234",
        is_active=True,
    )


@pytest.fixture
def auth_api(api, user):
    """Authenticated API client."""
    api.force_authenticate(user=user)
    return api


# -----------------------------------------------------------------------------------
# Sample Video object
# -----------------------------------------------------------------------------------
@pytest.fixture
def sample_video(db):
    """
    Minimal valid Video instance for content API tests.
    Avoids real file operations or external dependencies.
    """
    return Video.objects.create(
        title="Test Video",
        description="Sample video for testing.",
        video_file="videos/test.mp4",
        image_file="images/test.jpg",
    )


# -----------------------------------------------------------------------------------
# Mock boto3 (S3 client)
# -----------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_boto3(monkeypatch):
    """Prevent real AWS S3 operations."""
    def _mock_client(*args, **kwargs):
        class _MockS3:
            def generate_presigned_url(self, ClientMethod, Params=None, ExpiresIn=3600):
                key = (Params or {}).get("Key", "unknown")
                return f"https://mocked-s3-url.com/{key}?X-Amz-Signature=fake"
        return _MockS3()
    monkeypatch.setattr("boto3.client", _mock_client)


# -----------------------------------------------------------------------------------
# Mock django_rq queue (disable Redis queue connections)
# -----------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_rq_queue(monkeypatch):
    """Replace django_rq.get_queue() with dummy no-op implementation."""
    class _DummyQ:
        def enqueue(self, *args, **kwargs):
            return None
    monkeypatch.setattr("django_rq.get_queue", lambda *a, **k: _DummyQ())


# -----------------------------------------------------------------------------------
# Mock Redis cache globally for safety (in case of late imports)
# -----------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _force_local_cache(settings):
    """Re-assert LocMem cache inside test runtime."""
    settings.CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "videoflix-test-cache",
    }
    settings.CACHES["pages"] = settings.CACHES["default"]
