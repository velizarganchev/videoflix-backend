from django.apps import AppConfig
from django.db.models.signals import post_save


class ContentAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'content_app'

    def ready(self):
        from . import signals
