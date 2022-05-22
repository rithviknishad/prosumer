from django.apps import AppConfig

from prosumer.mqtt import update_state


class ProsumerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prosumer"

    def ready(self) -> None:
        update_state("isOnline", True)
