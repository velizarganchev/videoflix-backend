from django.urls import path
from .views import (
    RegisterView,
    ConfirmView,
    ForgotPasswordView,
    ResetPasswordView,

    JwtLoginView,
    JwtRefreshView,
    JwtLogoutView,

    ProfilesListView,
    SingleProfileView,
)
urlpatterns = [
    path("register/", RegisterView.as_view(), name="user-register"),
    path("confirm/", ConfirmView.as_view(), name="user-confirm"),

    path("forgot-password/", ForgotPasswordView.as_view(),
         name="user-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(),
         name="user-reset-password"),

    path("login/", JwtLoginView.as_view(), name="user-login"),
    path("refresh/", JwtRefreshView.as_view(), name="user-refresh"),
    path("logout/", JwtLogoutView.as_view(), name="user-logout"),

    path("profiles/", ProfilesListView.as_view(), name="user-profiles"),
    path("profiles/<int:pk>/", SingleProfileView.as_view(),
         name="user-profile-detail"),
]
