from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_GET

@require_GET
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return JsonResponse({
        "status": "ok" if db_status == "ok" else "error",
        "components": {
            "database": db_status,
            "cache": "ok"  # Fügen Sie hier Redis Checks hinzu
        }
    }, status=200 if db_status == "ok" else 503)