import os
from functools import cached_property
from typing import Final

from django.apps import AppConfig
from django.conf import settings

from prosumer.mqtt import ProsumerMqttClient
from prosumer.subsystems import Consumption, Generation, Storage
from utils.utils import acclimate_dict_for_kwargs

_ = acclimate_dict_for_kwargs


class ProsumerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prosumer"

    mqtt_client: Final[ProsumerMqttClient]

    generations: list[Generation] = []
    storages: list[Storage] = []
    consumptions: list[Consumption] = []

    @cached_property
    def config(self) -> dict[str, any]:
        return settings.PROSUMER_CONFIG

    @cached_property
    def settings(self) -> dict[str, any]:
        return self.config["settings"]

    def connect_to_grid(self) -> None:
        ProsumerConfig.mqtt_client = ProsumerMqttClient(
            vp_address=self.settings["vpAddress"],
            server=self.settings["server"],
            port=int(self.settings["mqttPort"]),
        )

    def initialize_subsystems(self):
        self.generations = [Generation(_(c)) for c in self.config["generations"]]
        self.storages = [Storage(_(c)) for c in self.config["storages"]]
        self.consumptions = [Consumption(_(c)) for c in self.config["consumptions"]]

    def ready(self) -> None:
        if os.environ.get("RUN_MAIN") != "true":
            self.connect_to_grid()
            self.mqtt_client.set_states(
                {
                    "isOnline": True,
                    **{
                        key: settings.PROSUMER_CONFIG[key]
                        for key in ["generations", "storages", "consumptions"]
                    },
                }
            )
            self.initialize_subsystems()
