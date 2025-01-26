from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import authenticate
from django.utils.http import int_to_base36, base36_to_int
from django.conf import settings
from rest_framework.permissions import AllowAny
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import status

from ..models import UserProfile
from .serializers import UserProfileSerializer


class GetUserProfilesView(APIView):
    """
    Handles the retrieval of all user profiles.

    Methods:
        get(request): Retrieves all user profiles and returns a list of their emails.

    Returns:
        Response: A JSON response containing a list of email addresses and HTTP 200 status.
    """

    def get(self, request):
        users = UserProfile.objects.all()
        emails = list(users.values_list('email', flat=True))
        return Response(emails, status=status.HTTP_200_OK)


class GetSingleUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    """
    Retrieves a single user profile by its ID.

    Permissions:
        IsAuthenticated: Only authenticated users can access this view.

    Methods:
        get(request, pk): Retrieves a user profile for the provided ID.

    Args:
        request (Request): The HTTP request object.
        pk (int): The primary key (ID) of the user profile.

    Returns:
        Response: Serialized user profile data with HTTP 200 if found.
        Response: Error message with HTTP 404 if the profile does not exist.
    """

    def get(self, request, pk):
        try:
            user = UserProfile.objects.get(id=pk)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class UserRegisterView(APIView):
    permission_classes = [AllowAny]
    """
    Handles user registration and sends a confirmation email.

    Permissions:
        AllowAny: Open to all users, regardless of authentication.

    Methods:
        post(request): Validates registration data, creates an inactive user, and sends a confirmation email.

    Args:
        request (Request): HTTP request with user registration data.

    Returns:
        Response: User email and HTTP 201 if registration is successful.
        Response: Validation errors with HTTP 400 if data is invalid.
    """

    def post(self, request):
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            # Save user with inactive status
            user = serializer.save(is_active=False)

            # Generate token and confirmation URL
            hashed_id = int_to_base36(user.id)
            token = Token.objects.get(user=user).key
            confirmation_url = f"{
                settings.BACKEND_URL}/users/confirm/?uid={hashed_id}&token={token}"

            # Render the email template
            html_content = render_to_string('../templates/emails/confirmation_email.html', {
                'user': user.username,
                'confirmation_url': confirmation_url
            })

            # Create the email
            subject = 'Confirm Your Email'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]

            email = EmailMultiAlternatives(
                subject, "Please confirm your email", from_email, to_email)
            # Attach the HTML content
            email.attach_alternative(html_content, "text/html")
            email.send()

            # Return success response
            return Response({'email': user.email}, status=status.HTTP_201_CREATED)

        # Return validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserConfirmationView(APIView):
    """
    Confirms user registration by validating a token and activating the user account.

    Methods:
        get(request): Validates the UID and token from query parameters and activates the user.

    Args:
        request (Request): HTTP request containing 'uid' and 'token' as query parameters.

    Returns:
        HttpResponseRedirect: Redirects to the frontend login URL on successful confirmation.
        Response: Error message with HTTP 400 if validation fails.
    """

    def get(self, request):
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')

        if not uid or not token:
            return Response({'error': 'Missing uid or token.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_token = Token.objects.get(key=token)
            user = user_token.user
        except (Token.DoesNotExist, ValueError, TypeError) as e:
            return Response({'error': f'Invalid or expired token. {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = base36_to_int(uid)
        except ValueError:
            return Response({'error': 'Invalid user ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.id != user_id:
            return Response({'error': 'User ID does not match the token.'}, status=status.HTTP_400_BAD_REQUEST)

        user_token.delete()
        Token.objects.get_or_create(user=user)
        user.is_active = True
        user.save()

        return HttpResponseRedirect(settings.FRONTEND_LOGIN_URL)


class UserLoginView(APIView):
    """
    Authenticates a user and returns their profile data if successful.

    Methods:
        post(request): Authenticates using the provided email and password.

    Args:
        request (Request): HTTP request containing 'email' and 'password'.

    Returns:
        Response: Serialized user profile and HTTP 200 if authentication is successful.
        ValidationError: HTTP 400 if credentials are invalid or missing.
    """

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            raise ValidationError(
                {'error': 'Email and password are required.'})

        user = authenticate(username=email, password=password)
        if user is None:
            raise ValidationError({'error': 'Invalid credentials.'})

        return Response({'user': UserProfileSerializer(user).data}, status=status.HTTP_200_OK)


class UserForgotPasswordView(APIView):
    """
    Handles password reset requests by sending a reset link to the user's email.

    Methods:
        post(request): Processes a password reset request by generating a token and sending an email.

    Args:
        request (Request): HTTP request containing the user's email.

    Returns:
        Response: A generic success message with HTTP 200, regardless of email existence.
        Response: Error message with HTTP 400 if the email field is missing.

    Security:
        Prevents user enumeration by not revealing whether the email exists in the system.
    """

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserProfile.objects.get(email=email)

            token = Token.objects.get(user=user).key
            uid = int_to_base36(user.id)

            reset_url = f"{settings.FRONTEND_RESET_PASSWORD_URL}?uid={
                uid}&token={token}"

            # Render the email template
            html_content = render_to_string('../templates/emails/reset_password_email.html', {
                'user': user.username,
                'reset_url': reset_url,
            })

            # Send the email
            subject = 'Reset Your Password'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]

            email_message = EmailMultiAlternatives(
                subject, "Click the link to reset your password.", from_email, recipient_list
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()

        except UserProfile.DoesNotExist:
            pass

        return Response({'message': 'If this email exists, a reset link has been sent.'}, status=status.HTTP_200_OK)


class UserResetPasswordView(APIView):
    """
    View to handle user password reset requests.
    Methods:
    -------
    post(request):
        Handles POST requests to reset the user's password.
    Parameters:
    ----------
    request : Request
        The HTTP request object containing 'uid', 'token', and 'new_password' in the request data.
    Returns:
    -------
    Response
        A Response object with a success message if the password is reset successfully,
        or an error message if any validation fails.
    """

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_token = Token.objects.get(key=token)
            user = user_token.user
        except (Token.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = base36_to_int(uid)
        except ValueError:
            return Response({'error': 'Invalid user ID.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.id != user_id:
            return Response({'error': 'User ID does not match the token.'}, status=status.HTTP_400_BAD_REQUEST)

        user_token.delete()
        Token.objects.get_or_create(user=user)

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)


class UserLogoutView(APIView):
    """
    Logs out the authenticated user by deleting their token.

    Permissions:
        IsAuthenticated: Requires the user to be logged in.

    Methods:
        post(request): Deletes the user's authentication token.

    Args:
        request (Request): The HTTP request from the logged-in user.

    Returns:
        Response: Success message with HTTP 200 if logout is successful.
        Response: Error message with HTTP 400 if the token does not exist.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({'error': 'Token not found. User may already be logged out.'}, status=status.HTTP_400_BAD_REQUEST)
 