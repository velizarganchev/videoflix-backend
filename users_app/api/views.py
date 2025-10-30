"""
users_app.api.views — User-facing API endpoints for Videoflix

Includes:
- Profiles: list all users, get single user
- Auth: register, confirm, login, logout
- Passwords: forgot/reset flows

Notes:
- Email sending is delegated to an RQ task (send_email_task) via django-rq.
- Tokens use DRF's Token model (one token per user).
- Confirmation / reset flows use base36 user id + token key.
"""

# used by send_email_task templates
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string   # used by email templates
from django.contrib.auth import authenticate
from django.utils.http import int_to_base36, base36_to_int
from django.http import HttpResponseRedirect
from django.conf import settings
from django_rq import get_queue

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework import status

from ..models import UserProfile
from .serializers import UserProfileSerializer
from ..tasks import send_email_task


# ----------------------------------------------------------------------
# Profiles
# ----------------------------------------------------------------------
class GetUserProfilesView(APIView):
    """
    Retrieve all user profiles.

    Methods:
        get(request): returns serialized list of users (all fields allowed by serializer).
    """

    def get(self, request):
        users = UserProfile.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetSingleUserProfileView(APIView):
    """
    Retrieve a single user profile by id.

    Permissions:
        IsAuthenticated — only logged-in users can access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """
        Args:
            pk (int): primary key for the target user profile.

        Returns:
            200 + serialized user data if found, else 404.
        """
        try:
            user = UserProfile.objects.get(id=pk)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ----------------------------------------------------------------------
# Registration & Confirmation
# ----------------------------------------------------------------------
class UserRegisterView(APIView):
    """
    Handle user registration and queue confirmation email.

    Permissions:
        AllowAny — open endpoint for sign-up.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Expects serializer-compatible payload (email, password, confirm_password, etc.)
        Creates an inactive user and sends confirmation via RQ.
        """
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            # Create inactive user; token is created by serializer get_token()
            user = serializer.save(is_active=False)

            # Compose confirmation URL using base36 uid + token
            hashed_id = int_to_base36(user.id)
            token = Token.objects.get(user=user).key
            confirmation_url = f"{settings.BACKEND_URL}/users/confirm/?uid={hashed_id}&token={token}"

            # Queue email sending task (subject, recipients, template, context)
            queue = get_queue("default")
            queue.enqueue(
                send_email_task,
                "Confirm Your Email",
                [user.email],
                "../templates/emails/confirmation_email.html",
                {"user": user.username, "confirmation_url": confirmation_url},
            )

            return Response({"email": user.email}, status=status.HTTP_201_CREATED)

        # Validation errors (unique email, password mismatch, etc.)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserConfirmationView(APIView):
    """
    Confirm registration by validating token + base36 uid and activating the account.

    On success: redirects to frontend login page.
    """

    def get(self, request):
        """
        Query params:
            uid (str, base36), token (str)

        Returns:
            302 redirect to FRONTEND_LOGIN_URL on success, else 400 with details.
        """
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return Response(
                {"error": "Missing uid or token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate token → get user
        try:
            user_token = Token.objects.get(key=token)
            user = user_token.user
        except (Token.DoesNotExist, ValueError, TypeError) as e:
            return Response(
                {"error": f"Invalid or expired token. {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate base36 uid and match to token user
        try:
            user_id = base36_to_int(uid)
        except ValueError:
            return Response(
                {"error": "Invalid user ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.id != user_id:
            return Response(
                {"error": "User ID does not match the token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rotate token (delete old, ensure new exists) and activate
        user_token.delete()
        Token.objects.get_or_create(user=user)
        user.is_active = True
        user.save()

        return HttpResponseRedirect(settings.FRONTEND_LOGIN_URL)


# ----------------------------------------------------------------------
# Login / Logout
# ----------------------------------------------------------------------
class UserLoginView(APIView):
    """
    Authenticate user by email + password and return serialized profile (with token).
    """

    def post(self, request):
        """
        Expects:
            email, password

        Returns:
            200 + user data on success; 400 + error on missing/invalid credentials.
        """
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            raise ValidationError(
                {"error": "Email and password are required."})

        # NB: username is email in this project setup
        # Debug print (kept intentionally; remove in production)
        print(email, password)
        user = authenticate(username=email, password=password)
        if user is None or not user.is_active:
            raise ValidationError({"error": "Invalid credentials."})

        return Response(UserProfileSerializer(user).data, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    Logout by deleting the user's auth token.

    Permissions:
        IsAuthenticated — token must exist.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Deletes token and returns a generic success/error response.
        Token deletion is also enqueued once (as in current logic).
        """
        try:
            queue = get_queue("default")
            # Enqueue token deletion (kept as-is), then delete explicitly below:
            queue.enqueue(Token.objects.filter(user=request.user).delete)
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response(
                {"message": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Token.DoesNotExist:
            return Response(
                {"error": "Token not found. User may already be logged out."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ----------------------------------------------------------------------
# Password reset flow
# ----------------------------------------------------------------------
class UserForgotPasswordView(APIView):
    """
    Start password reset: generate token + uid and send reset link via email.

    Security:
        Avoids user enumeration by always returning 200.
    """

    def post(self, request):
        """
        Expects:
            email

        Returns:
            200 with generic message (email may or may not exist).
        """
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = UserProfile.objects.get(email=email)

            token = Token.objects.get(user=user).key
            uid = int_to_base36(user.id)
            reset_url = f"{settings.FRONTEND_RESET_PASSWORD_URL}?uid={uid}&token={token}"

            # Queue reset email
            queue = get_queue("default")
            queue.enqueue(
                send_email_task,
                "Reset Your Password",
                [user.email],
                "../templates/emails/reset_password_email.html",
                {"user": user.username, "reset_url": reset_url},
            )
        except UserProfile.DoesNotExist:
            # Swallow error to prevent enumeration
            pass

        return Response(
            {"message": "If this email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class UserResetPasswordView(APIView):
    """
    Complete password reset by validating token + uid and setting the new password.
    """

    def post(self, request):
        """
        Expects:
            uid (base36), token, new_password

        Returns:
            200 on success; 400 with error details otherwise.
        """
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not uid or not token or not new_password:
            return Response(
                {"error": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate token → get user
        try:
            user_token = Token.objects.get(key=token)
            user = user_token.user
        except (Token.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate base36 uid and match
        try:
            user_id = base36_to_int(uid)
        except ValueError:
            return Response(
                {"error": "Invalid user ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.id != user_id:
            return Response(
                {"error": "User ID does not match the token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rotate token, set new password
        user_token.delete()
        Token.objects.get_or_create(user=user)
        user.set_password(new_password)
        user.save()

        # Notify via email
        queue = get_queue("default")
        queue.enqueue(
            send_email_task,
            "Your Password Has Been Reset",
            [user.email],
            "../templates/emails/password_reset_success.html",
            {"user": user.username},
        )

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
