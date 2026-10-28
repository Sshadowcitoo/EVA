from django.apps import AppConfig


class CapturaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.captura'

    def ready(self):
        from config import capture_checks  # noqa: F401
