#!/usr/bin/env sh
set -eu

# Ensure created files/dirs are world-readable (nginx needs to read media)
# Files: 644, Dirs: 755 (unless app explicitly overrides)
umask 022

echo "[entrypoint] umask=$(umask)"
echo "[entrypoint] CMD args: $*"
CMD="${1:-web}"

wait_for_db() {
  echo "[entrypoint] Waiting for database..."
  python - <<'PY'
import os, time, sys
import psycopg2

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))
name = os.environ.get("DB_NAME", "")
user = os.environ.get("DB_USER", "")
pwd  = os.environ.get("DB_PASSWORD", "")

# If DB env is not set, skip waiting (useful for DEBUG/SQLite)
if not (name and user and host):
    print("[entrypoint] DB env not fully set, skipping DB wait.")
    sys.exit(0)

for i in range(40):  # ~40 * 1.5s = 60s max
    try:
        conn = psycopg2.connect(
            dbname=name, user=user, password=pwd,
            host=host, port=port,
            connect_timeout=3
        )
        conn.close()
        print("[entrypoint] Database is ready.")
        sys.exit(0)
    except Exception:
        time.sleep(1.5)

print("[entrypoint] Database not reachable after timeout.")
sys.exit(1)
PY
}

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-videoflix_backend_app.settings}"

if [ "$CMD" = "web" ]; then
  wait_for_db

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
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "videoflix_backend_app.settings"))
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

  echo "[entrypoint] Starting gunicorn (web)..."
  exec gunicorn videoflix_backend_app.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-2}" \
      --timeout "${GUNICORN_TIMEOUT:-120}" \
      --forwarded-allow-ips='*'

elif [ "$CMD" = "worker" ]; then
  wait_for_db
  echo "[entrypoint] Starting RQ worker..."
  exec python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker

else
  echo "[entrypoint] Running custom command: $*"
  exec "$@"
fi
