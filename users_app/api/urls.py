"""
users_app.api.urls

Defines all API endpoints for user-related actions in the Videoflix backend.

Includes:
- User registration, confirmation, login, logout
- Password reset and recovery
- Profile retrieval (all users and single user)
"""

from django.urls import path
from .views import (
    GetUserProfilesView,
    GetSingleUserProfileView,
    UserRegisterView,
    UserConfirmationView,
    UserLoginView,
    UserLogoutView,
    UserForgotPasswordView,
    UserResetPasswordView,
)

# ----------------------------------------------------------------------
# User API Endpoints
# ----------------------------------------------------------------------
urlpatterns = [
    # --- Profile Management ---
    path("profiles/", GetUserProfilesView.as_view(), name="profiles"),
    path("profile/<int:pk>/", GetSingleUserProfileView.as_view(), name="profile"),

    # --- Authentication & Registration ---
    path("register/", UserRegisterView.as_view(), name="register"),
    path("confirm/", UserConfirmationView.as_view(), name="user-confirmation"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),

    # --- Password Management ---
    path("forgot-password/", UserForgotPasswordView.as_view(),
         name="forgot-password"),
    path("reset-password/", UserResetPasswordView.as_view(),
         name="reset-password"),
]
