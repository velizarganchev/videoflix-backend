#!/usr/bin/env sh
set -euo pipefail

echo "[entrypoint] Running Django checks..."
python manage.py check || true

echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo "[entrypoint] Ensuring superuser exists..."
  python - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "videoflix_backend_app.settings")
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.environ.get("DJANGO_SUPERUSER_USERNAME")
p = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
e = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
if u and p:
    if not User.objects.filter(username=u).exists():
        User.objects.create_superuser(username=u, password=p, email=e)
        print(f"[entrypoint] Superuser '{u}' created.")
    else:
        print(f"[entrypoint] Superuser '{u}' already exists.")
PY
fi

CMD="${1:-web}"

if [ "$CMD" = "web" ]; then
  echo "[entrypoint] Starting gunicorn (web)..."
  exec gunicorn videoflix_backend_app.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-4}" \
      --timeout "${GUNICORN_TIMEOUT:-120}" \
      --forwarded-allow-ips='*'
elif [ "$CMD" = "worker" ]; then
  echo "[entrypoint] Starting RQ worker..."
  exec python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker
else
  echo "[entrypoint] Running custom command: $*"
  exec "$@"
fi
