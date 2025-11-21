"""
User management endpoints for the Videoflix backend.

Implements authentication and user lifecycle flows using:
- Django REST Framework (DRF)
- RQ background tasks for sending emails

Endpoints:
-----------
POST   /users/register/         → Register a new inactive user + send confirmation email
GET    /users/confirm/          → Activate account via confirmation link
POST   /users/login/            → Login and issue JWT cookies
POST   /users/refresh/          → Refresh JWT access token
POST   /users/logout/           → Logout and clear cookies
GET    /users/profiles/         → List all profiles (admin scope)
GET    /users/profiles/<pk>/    → Retrieve single user profile
POST   /users/forgot-password/  → Request password reset link
POST   /users/reset-password/   → Set new password using reset token
"""

from django.utils.http import int_to_base36, base36_to_int
from django.http import HttpResponseRedirect
from django.conf import settings

from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle

from django_rq import get_queue
from rest_framework_simplejwt.tokens import RefreshToken, TokenError, AccessToken

from ..models import UserProfile
from .serializers import EmailQuerySerializer, UserPublicSerializer, RegisterSerializer, LoginSerializer
from ..tasks import send_email_task
from .auth import set_auth_cookies, clear_auth_cookies


class EmailExistsView(APIView):
    """
    GET /users/email-exists/?email=<addr>
    Returns: { "exists": true|false }

    Notes:
    - Public endpoint; validates email format.
    - Case-insensitive lookup.
    - Throttled to reduce enumeration risk.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        ser = EmailQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        exists = UserProfile.objects.filter(email__iexact=email).exists()
        return Response({"exists": exists}, status=200)


class RegisterView(CreateAPIView):
    """
    POST /users/register/
    Handles new user registration.

    Uses RegisterSerializer for input validation, creates an inactive user,
    and enqueues a confirmation email with a short-lived JWT access token.
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    queryset = UserProfile.objects.all()

    def perform_create(self, serializer):
        user: UserProfile = serializer.save(is_active=False)
        token = str(RefreshToken.for_user(user).access_token)
        uid = int_to_base36(user.id)
        confirmation_url = f"{settings.FRONTEND_CONFIRM_URL}?uid={uid}&token={token}"

        if settings.DEBUG:
            self._debug_confirm = {
                "uid": uid,
                "token": token,
                "confirmation_url": confirmation_url,
            }
            send_email_task(
                "Confirm Your Videoflix Account",
                [user.email],
                "emails/confirmation_email.html",
                {"user": user.username, "confirmation_url": confirmation_url,
                    "logo_url": "https://videoflix.velizar-ganchev.com/assets/images/logo.png"},
            )
        else:
            queue = get_queue("default")
            queue.enqueue(
                send_email_task,
                "Confirm Your Videoflix Account",
                [user.email],
                "emails/confirmation_email.html",
                {"user": user.username, "confirmation_url": confirmation_url,
                    "logo_url": "https://videoflix.velizar-ganchev.com/assets/images/logo.png"},
            )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        payload = {"email": response.data.get("email")}

        if settings.DEBUG and hasattr(self, "_debug_confirm"):
            payload["debug"] = self._debug_confirm
        return Response(payload, status=status.HTTP_201_CREATED)


class ConfirmView(APIView):
    """
    GET /users/confirm/?uid=<base36>&token=<jwt>
    Activates the user account from the confirmation link.

    Security:
    - Validates the provided AccessToken.
    - Ensures token subject matches the uid.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")
        if not uid or not token:
            return Response({"error": "Missing uid or token."}, status=400)

        try:
            user_id = base36_to_int(uid)

            at = AccessToken(token)
            if int(at.get("user_id")) != user_id:
                return Response({"error": "Token does not match user."}, status=400)

            user = UserProfile.objects.get(id=user_id)
        except TokenError:
            return Response({"error": "Invalid or expired token."}, status=400)
        except Exception:
            return Response({"error": "Invalid user ID."}, status=400)

        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        return HttpResponseRedirect(settings.FRONTEND_LOGIN_URL)


class JwtRefreshView(APIView):
    """
    POST /users/refresh/
    Uses the refresh cookie to issue a new access token.
    If ROTATE_REFRESH_TOKENS is enabled, mints a new refresh too (and
    blacklists the old one when BLACKLIST_AFTER_ROTATION is enabled).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_cookie_name = getattr(
            settings, "JWT_REFRESH_COOKIE_NAME", "vf_refresh")
        raw_refresh = request.COOKIES.get(refresh_cookie_name)
        if not raw_refresh:
            return Response({"error": "Missing refresh cookie."}, status=401)

        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError:
            return Response({"error": "Invalid refresh token."}, status=401)

        # Always create a fresh access token
        access = str(refresh.access_token)
        resp = Response({"detail": "Access token refreshed."}, status=200)
        resp.set_cookie(
            getattr(settings, "JWT_ACCESS_COOKIE_NAME", "vf_access"),
            access,
            max_age=5 * 60,
            httponly=True,
            secure=getattr(settings, "JWT_COOKIE_SECURE", True),
            samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
            path="/",
        )

        rotate = settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False)
        blacklist_after = settings.SIMPLE_JWT.get(
            "BLACKLIST_AFTER_ROTATION", False)

        if rotate:
            if blacklist_after:
                try:
                    refresh.blacklist()
                except Exception:
                    pass

            try:
                user_id = int(refresh.get("user_id"))
                user = UserProfile.objects.get(pk=user_id)
                new_refresh = RefreshToken.for_user(user)
                resp.set_cookie(
                    refresh_cookie_name,
                    str(new_refresh),
                    max_age=7 * 24 * 60 * 60,
                    httponly=True,
                    secure=getattr(settings, "JWT_COOKIE_SECURE", True),
                    samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
                    path="/",
                )
            except Exception:
                pass

        return resp


class JwtLoginView(APIView):
    """
    POST /users/login/
    Authenticates the user and sets JWT tokens in HttpOnly cookies.

    Flow:
    - Validate input with LoginSerializer (email, password).
    - On success, issue Refresh/Access tokens and set cookies.
    - Return safe public profile data.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        remember = bool(request.data.get("remember", False))

        refresh = RefreshToken.for_user(user)
        data = UserPublicSerializer(user).data
        response = Response(data, status=200)
        set_auth_cookies(response, refresh, remember)
        return response


class JwtLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_cookie_name = getattr(
            settings, "JWT_REFRESH_COOKIE_NAME", "vf_refresh")
        raw_refresh = request.COOKIES.get(refresh_cookie_name)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except Exception:
                pass
        resp = Response({"message": "Successfully logged out."}, status=200)
        clear_auth_cookies(resp)
        return resp


class ForgotPasswordView(GenericAPIView):
    """
    POST /users/forgot-password/
    Sends a password reset email to the user if the address exists.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"error": "Email is required."}, status=400)

        try:
            user = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            return Response({"message": "If this email exists, a reset link has been sent."}, status=200)

        token = str(RefreshToken.for_user(user).access_token)
        uid = int_to_base36(user.id)
        reset_url = f"{settings.FRONTEND_RESET_PASSWORD_URL}?uid={uid}&token={token}"

        if settings.DEBUG:
            send_email_task(
                "Reset Your Password",
                [user.email],
                "emails/reset_password_email.html",
                {"user": user.username, "reset_url": reset_url,
                    "logo_url": "https://videoflix.velizar-ganchev.com/assets/images/logo.png"},
            )
        else:
            queue = get_queue("default")
            queue.enqueue(
                send_email_task,
                "Reset Your Password",
                [user.email],
                "emails/reset_password_email.html",
                {"user": user.username, "reset_url": reset_url,
                    "logo_url": "https://videoflix.velizar-ganchev.com/assets/images/logo.png"},
            )

        payload = {"message": "If this email exists, a reset link has been sent."}
        if settings.DEBUG:
            payload["debug"] = {"uid": uid,
                                "token": token, "reset_url": reset_url}
        return Response(payload, status=200)


class ResetPasswordView(GenericAPIView):
    """
    POST /users/reset-password/
    Resets a user's password using a valid token and user ID.

    Security:
    - Validates AccessToken.
    - Ensures token subject matches the uid.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not uid or not token or not new_password:
            return Response({"error": "All fields are required."}, status=400)

        try:
            user_id = base36_to_int(uid)

            at = AccessToken(token)
            if int(at.get("user_id")) != user_id:
                return Response({"error": "Token does not match user."}, status=400)

            user = UserProfile.objects.get(id=user_id)
        except TokenError:
            return Response({"error": "Invalid or expired token."}, status=400)
        except Exception:
            return Response({"error": "Invalid user."}, status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"message": "Password has been reset successfully."}, status=200)
