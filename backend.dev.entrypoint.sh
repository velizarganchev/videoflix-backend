#!/usr/bin/env sh
set -e

echo ">>> Applying migrations..."
python manage.py migrate --noinput

echo ">>> Ensuring default dev superuser exists..."
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model

User = get_user_model()
username = "admin"
email = "admin@example.com"
password = "adminpassword"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser 'admin' created (admin/adminpassword).")
else:
    print("Superuser 'admin' already exists.")
EOF

if [ "$1" = "worker" ]; then
    echo ">>> Starting RQ worker..."
    python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker
else
    echo ">>> Starting development server..."
    python manage.py runserver 0.0.0.0:8000
fi
