import os
from functools import cached_property
from typing import Final

from django.apps import AppConfig
from django.conf import settings
from utils.utils import acclimate_dict_for_kwargs

from prosumer.mqtt import ProsumerMqttClient
from prosumer.subsystems import (
    Consumption,
    Generation,
    InterconnectedSubsystem,
    Storage,
)


class ProsumerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prosumer"

    mqtt_client: Final[ProsumerMqttClient]

    master_subsystem: InterconnectedSubsystem

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
        _ = acclimate_dict_for_kwargs
        consumptions = [Consumption(**_(c)) for c in self.config["consumptions"]]
        generations = [Generation(**_(c)) for c in self.config["generations"]]
        storages = [Storage(**_(c)) for c in self.config["storages"]]
        self.master_subsystem = InterconnectedSubsystem(
            consumptions=consumptions,
            generations=generations,
            storages=storages,
            set_states=self.mqtt_client.set_states,
            id=-1,
        )

    def ready(self) -> None:
        if os.environ.get("RUN_MAIN") != "true":
            return
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
