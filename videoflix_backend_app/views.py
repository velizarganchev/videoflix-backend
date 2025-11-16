"""
views.py — Health Check Endpoint for Videoflix Backend

Provides a simple JSON response indicating service health.

Checks performed:
- Database connectivity (simple SELECT 1)
- Cache (placeholder; extend to include Redis connection check)

Returns HTTP 200 if all checks pass, otherwise 503.
"""

from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """
    Health-check endpoint.

    Used by Docker, load balancers, or uptime monitors
    to verify that the backend and database are operational.

    Returns:
        JSON response:
        {
            "status": "ok" | "error",
            "components": {
                "database": "ok" | "error: <message>",
                "cache": "ok" | "error: <message>"
            }
        }
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return JsonResponse(
        {
            "status": "ok" if db_status == "ok" else "error",
            "components": {
                "database": db_status,
                "cache": "ok",
            },
        },
        status=200 if db_status == "ok" else 503,
    )
