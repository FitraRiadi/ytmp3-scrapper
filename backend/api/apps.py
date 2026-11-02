from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        # siapkan worker konversi (idempotent)
        from api import jobs

        jobs.bootstrap()
