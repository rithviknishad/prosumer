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
        moving_avg_periods = self.config.get("moving_avg_periods", [])
        subsystem_reporting = tuple(self.config.get("subsystem_reporting", []))
        commons = {
            "moving_avg_periods": moving_avg_periods,
        }
        acclimate = acclimate_dict_for_kwargs
        consumptions = [
            Consumption(**commons, **acclimate(config))
            for config in self.config.get("consumptions", [])
        ]
        generations = [
            Generation(**commons, **acclimate(config))
            for config in self.config.get("generations", [])
        ]
        storages = [
            Storage(**commons, **acclimate(config))
            for config in self.config.get("storages", [])
        ]
        self.master_subsystem = InterconnectedSubsystem(
            **commons,
            consumptions=consumptions,
            generations=generations,
            storages=storages,
            set_states=self.mqtt_client.set_states,
            subsystem_reporting=subsystem_reporting,
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
                    for key in [
                        "generations",
                        "storages",
                        "consumptions",
                        "location",
                        "moving_avg_periods",
                    ]
                },
            }
        )
        self.initialize_subsystems()
