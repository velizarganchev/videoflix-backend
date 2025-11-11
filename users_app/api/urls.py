from django.urls import path
from .views import (
    EmailExistsView,
    RegisterView,
    ConfirmView,
    ForgotPasswordView,
    ResetPasswordView,

    JwtLoginView,
    JwtRefreshView,
    JwtLogoutView,
)
urlpatterns = [
    path("email-exists/", EmailExistsView.as_view(), name="user-email-exists"),
    path("register/", RegisterView.as_view(), name="user-register"),
    path("confirm/", ConfirmView.as_view(), name="user-confirm"),

    path("forgot-password/", ForgotPasswordView.as_view(),
         name="user-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(),
         name="user-reset-password"),

    path("login/", JwtLoginView.as_view(), name="user-login"),
    path("refresh/", JwtRefreshView.as_view(), name="user-refresh"),
    path("logout/", JwtLogoutView.as_view(), name="user-logout"),
]
