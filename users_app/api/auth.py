from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def set_auth_cookies(response, refresh: RefreshToken, remember: bool = False):
    """
    Sets JWT authentication cookies (access + refresh) on the HTTP response.

    - Access token: short-lived (default 5 minutes)
    - Refresh token: 1 hour by default, or 7 days if 'remember' is True
    - Both cookies are HttpOnly and secured by default (no JS access)

    Args:
        response: DRF or Django HTTP response object
        refresh: SimpleJWT RefreshToken instance
        remember: If True, extends refresh token lifetime (persistent login)

    Returns:
        Modified response with authentication cookies attached
    """
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # Access cookie – 5 minutes lifetime
    response.set_cookie(
        key=getattr(settings, "JWT_ACCESS_COOKIE_NAME", "vf_access"),
        value=access_token,
        max_age=5 * 60,
        httponly=True,
        secure=getattr(settings, "JWT_COOKIE_SECURE", True),
        samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
        path="/",
    )

    # Refresh cookie – 7 days if "remember" is True, otherwise 1 hour
    refresh_age = 7 * 24 * 60 * 60 if remember else 60 * 60
    response.set_cookie(
        key=getattr(settings, "JWT_REFRESH_COOKIE_NAME", "vf_refresh"),
        value=refresh_token,
        max_age=refresh_age,
        httponly=True,
        secure=getattr(settings, "JWT_COOKIE_SECURE", True),
        samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
        path="/",
    )
    return response


def clear_auth_cookies(response):
    """
    Removes JWT authentication cookies from the HTTP response.

    Used during logout or session invalidation.
    """
    response.delete_cookie(
        getattr(settings, "JWT_ACCESS_COOKIE_NAME", "vf_access"), path="/"
    )
    response.delete_cookie(
        getattr(settings, "JWT_REFRESH_COOKIE_NAME", "vf_refresh"), path="/"
    )
    return response
