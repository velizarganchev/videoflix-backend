"""
content_app.apps — App configuration for Videoflix content module

Purpose:
--------
Defines application metadata and initialization logic for the content_app.
Automatically imports signal handlers when the app is ready.
"""

from django.apps import AppConfig


class ContentAppConfig(AppConfig):
    """
    Configuration class for the content_app.

    Attributes:
        default_auto_field (str): Default field type for model primary keys.
        name (str): The app name used by Django to register the app.

    Methods:
        ready():
            Imports and activates signal handlers for the app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "content_app"

    def ready(self):
        """Import signals to ensure they are registered when the app loads."""
        from . import signals
