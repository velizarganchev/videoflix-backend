from django.apps import AppConfig


class ContentAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'content_app'

    def ready(self):
        from . import signals
