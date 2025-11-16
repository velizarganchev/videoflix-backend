from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class for Videoflix.

    Authentication flow:
    1) Attempts to read and validate the JWT access token from an HttpOnly cookie (default: "vf_access").
    2) If no valid cookie is found, falls back to the standard "Authorization: Bearer <token>" header.

    This allows seamless authentication for frontend clients using secure cookies
    while keeping compatibility with API tools (Postman, etc.).
    """

    def authenticate(self, request):
        cookie_name = getattr(settings, "JWT_ACCESS_COOKIE_NAME", "vf_access")
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token:
            validated = self.get_validated_token(raw_token)
            return (self.get_user(validated), validated)

        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated = self.get_validated_token(raw_token)
        return (self.get_user(validated), validated)
