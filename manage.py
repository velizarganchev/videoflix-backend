"""Django's command-line utility for administrative tasks."""
import os
import sys

if not os.getenv("ENV_FILE"):
    # Prefer .env.dev if present (for local dev)
    if os.path.exists(".env.dev"):
        os.environ["ENV_FILE"] = ".env.dev"
    # else fall back to .env if present
    elif os.path.exists(".env"):
        os.environ["ENV_FILE"] = ".env"


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'videoflix_backend_app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
