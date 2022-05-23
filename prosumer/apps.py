from django.apps import AppConfig
from django.conf import settings

from prosumer.mqtt import set_states


class ProsumerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prosumer"

    def ready(self) -> None:
        set_states(
            {
                "isOnline": True,
                **{
                    key: settings.PROSUMER_CONFIG[key]
                    for key in ["generations", "storages", "consumptions"]
                },
            }
        )
