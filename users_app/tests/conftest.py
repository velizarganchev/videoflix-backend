import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.permissions import AllowAny, IsAuthenticated


# --------------------------------------------------------------------------
# DRF test client
# --------------------------------------------------------------------------
@pytest.fixture
def api():
    """Provides a DRF APIClient instance for making HTTP requests in tests."""
    return APIClient()


# --------------------------------------------------------------------------
# User model fixture
# --------------------------------------------------------------------------
@pytest.fixture
def User():
    """Returns the active Django user model."""
    return get_user_model()


# --------------------------------------------------------------------------
# User fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def user_inactive(db, User):
    """Creates an inactive user (used for register/confirm tests)."""
    return User.objects.create_user(
        username="inactive@example.com",
        email="inactive@example.com",
        password="pass1234",
        is_active=False,
    )


@pytest.fixture
def user_active(db, User):
    """Creates an active user (used for login/password flow tests)."""
    return User.objects.create_user(
        username="active@example.com",
        email="active@example.com",
        password="pass1234",
        is_active=True,
    )


# --------------------------------------------------------------------------
# Mock RQ queue – replaces the real Redis connection during tests
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _mock_rq_queue(monkeypatch):
    """
    Automatically replaces `django_rq.get_queue` with a dummy queue that
    simply records enqueue calls. Prevents Redis connection errors in tests.
    """
    class DummyQueue:
        def __init__(self):
            self.calls = []

        def enqueue(self, fn, *args, **kwargs):
            self.calls.append((getattr(fn, "__name__", str(fn)), args, kwargs))

    q = DummyQueue()
    monkeypatch.setattr("users_app.api.views.get_queue", lambda *a, **k: q)
    return q


# --------------------------------------------------------------------------
# Permission setup
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _permissions_setup(settings, monkeypatch):
    """
    Globally enforces authentication for all API views, except for a few
    explicitly public endpoints (register, confirm, forgot/reset password, login).
    The `/users/profiles/` endpoint is explicitly protected.
    """
    # Default: all views require authentication
    settings.REST_FRAMEWORK = {
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated"
        ]
    }

    from users_app.api import views as user_views

    # Explicitly public endpoints
    public_views = [
        "UserRegisterView",
        "UserConfirmationView",
        "UserForgotPasswordView",
        "UserResetPasswordView",
        "UserLoginView",
    ]
    for name in public_views:
        if hasattr(user_views, name):
            cls = getattr(user_views, name)
            monkeypatch.setattr(cls, "permission_classes",
                                [AllowAny], raising=False)

    # Explicitly require authentication for /users/profiles/
    if hasattr(user_views, "GetUserProfilesView"):
        monkeypatch.setattr(
            user_views.GetUserProfilesView,
            "permission_classes",
            [IsAuthenticated],
            raising=False,
        )
