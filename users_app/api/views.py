from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework import status

from django.core.mail import send_mail
from django.contrib.auth import authenticate
from django.utils.http import int_to_base36, base36_to_int
from django.conf import settings

from users_app.models import UserProfile
from .serializers import UserProfileSerializer


class GetUserProfilesView(APIView):
    permission_classes = [IsAuthenticated]
    """
    GetUserProfilesView handles the retrieval of all user profiles.
    Methods:
        get(request):
            Handles the GET request to retrieve all user profiles.
            - Retrieves all user profiles from the database.
            - Serializes the user profiles.
            - Returns only the emails of the user profiles with HTTP 200 status.
    """

    def get(self, request):
        users = UserProfile.objects.all()
        emails = users.values_list('email', flat=True)
        return Response({'emails': emails}, status=status.HTTP_200_OK)


class GetSingleUserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    """
    GetSingleUserProfileView handles the retrieval of a single user profile.
    Methods:
        get(request, pk):
            Handles the GET request to retrieve a single user profile.
            Args:
                request: The HTTP request object.
                pk: The ID of the user profile to retrieve.
            - Retrieves the user profile from the database using the user ID.
            - Serializes the user profile.
            - Returns the serialized user profile with HTTP 200 status.
            - Returns an error message with HTTP 404 status if the user profile does not exist.
    """

    def get(self, request, pk):
        try:
            user = UserProfile.objects.get(id=pk)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class UserRegisterView(APIView):
    """
    User registration view that handles user sign-up and sends a confirmation email.
    Methods:
        post(request):
            Handles the POST request to register a new user.
            - Validates the user data using UserProfileSerializer.
            - If valid, saves the user with is_active set to False.
            - Generates a confirmation URL with a hashed user ID and token.
            - Sends a confirmation email to the user with the confirmation URL.
            - Returns a success message with HTTP 201 status if registration is successful.
            - Returns validation errors with HTTP 400 status if registration fails.
    """

    def post(self, request):
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(is_active=False)

            hashed_id = int_to_base36(user.id)
            token = Token.objects.get(user=user).key

            confirmation_url = f"{settings.FRONTEND_REGISTER_URL}?uid={
                hashed_id}&token={token}"

            send_mail(
                subject='Confirm Your Email',
                message=f'Click the link to confirm your registration: {
                    confirmation_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            return Response({'message': 'Please check your email to confirm registration.', 'created': True}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserConfirmationView(APIView):
    """
    UserConfirmationView handles the confirmation of a user's email address via a token.
    Methods:
        get(request, uid, token):
            Handles GET requests to confirm a user's email address.
            Args:
                request: The HTTP request object.
                uid: The user's ID in base36 format.
                token: The token associated with the user.
            Returns:
                Response: A Response object with a success message and new token if the email is confirmed,
                          or an error message if the token is invalid or expired, or if the user ID is invalid.
    """

    def get(self, request, uid, token):
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
        new_token, created = Token.objects.get_or_create(user=user)
        user.is_active = True
        user.save()

        return Response({'message': 'Email successfully confirmed. You can now log in.', 'token': new_token.key}, status=status.HTTP_200_OK)


class UserLoginView(APIView):
    """
    UserLoginView handles user login requests.
    Methods:
        post(request):
            Authenticates a user based on email and password provided in the request data.
            Returns a serialized user profile if authentication is successful.
            Raises ValidationError if email or password is missing or if credentials are invalid.
    Args:
        request (Request): The HTTP request object containing user login data.
    Returns:
        Response: A response object containing the serialized user profile and HTTP status 200 if authentication is successful.
    Raises:
        ValidationError: If email or password is missing or if credentials are invalid.
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
    UserForgotPasswordView handles the password reset request for a user.
    Methods:
        post(request):
            Handles POST requests to initiate the password reset process.
            - Retrieves the email from the request data.
            - If the email is not provided, returns a 400 Bad Request response.
            - If the email exists in the UserProfile database, generates a reset token and UID.
            - Constructs a password reset URL and sends it to the user's email.
            - If the email does not exist, returns a generic success message to avoid revealing user information.
            Args:
                request (Request): The HTTP request object containing the email.
            Returns:
                Response: A response indicating whether the reset link was sent or not.
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
                uid}&token={token.key}"

            send_mail(
                subject='Reset Your Password',
                message=f'Click the link to reset your password: {reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )

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
    UserLogoutView handles the user logout process.
    This view requires the user to be authenticated. It attempts to retrieve the
    authentication token associated with the user making the request and deletes it,
    effectively logging the user out.
    Methods:
        post(request): Handles the POST request to log out the user by deleting their token.
    Raises:
        Token.DoesNotExist: If the token does not exist, indicating the user may already be logged out.
    Returns:
        Response: A response indicating the success or failure of the logout process.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({'error': 'Token not found. User may already be logged out.'}, status=status.HTTP_400_BAD_REQUEST)
