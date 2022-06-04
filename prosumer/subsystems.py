from datetime import datetime, timedelta
from functools import cached_property
from random import uniform
from typing import Callable, Final, Optional
from prosumer.enums import ProsumerStatus
from utils.utils import Base
from utils.decorators import setInterval
from utils.mixins import states_setter
from utils.interpolate import Curves, remap


class SubsystemBase(Base):
    """
    Base class for a subsystem.
    """

    run_interval = 1
    auto_start = True

    def __init__(self, **kwargs) -> None:
        self.id_ = str(kwargs.pop("id"))
        self.auto_start = bool(kwargs.pop("auto_start", SubsystemBase.auto_start))
        self.runner: any = None

        super().__init__(**kwargs)

        if self.auto_start:
            self.start()

    def start(self):
        """
        Starts running the subsystem.
        Does nothing if runner already exists.
        """
        if getattr(self, "runner", False):
            return
        self.started_at = datetime.now()
        self.runner = self.run()

    def stop(self):
        """
        Stops running the subsystem, and clears the runner.
        """
        self.runner.stop()
        self.runner = None

    @setInterval(run_interval)
    def run(self):
        """
        The function that executes every `run_interval` seconds once the
        subsystem is running.
        """
        self.on_run()

    def on_run(self):
        raise NotImplementedError("run")


# Predefined ranges
_RANGE_30M: Final[int] = 30 * 60


class SubsystemWithProfile(SubsystemBase):

    profile_interval: int
    profile_base_multiplier_field_name: str

    def __init__(self, **kwargs) -> None:
        self.profile: dict = kwargs.pop("profile")
        self.power = 0.0
        super().__init__(**kwargs)
        self.compiled_profile = self.generate_profile()

    def generate_profile(self) -> list:
        """
        Attempts to parse profile from `self.config` and generates profile
        between `r0` and `r1` bounds for `7 days`
        """
        if self.profile["source"] == "range_30m":
            base_multiplier = float(
                getattr(self, self.profile_base_multiplier_field_name)
            )
            self.profile_interval = _RANGE_30M
            p_bounds = zip(self.profile["r0"] * 7, self.profile["r1"] * 7)
            return [base_multiplier * uniform(*i) for i in p_bounds]
        raise NotImplementedError(f"{self.profile['source']} not supported")

    @cached_property
    def date_started_at(self):
        d = self.started_at.date()
        return datetime(d.year, d.month, d.day)

    def get_value(self, instant: datetime | None = None):
        instant = instant or datetime.now()
        profile = self.compiled_profile
        delta = instant - self.date_started_at
        lower_idx = delta.seconds // self.profile_interval
        interop_x = delta.seconds / self.profile_interval % 1
        lower, upper = profile[lower_idx], profile[lower_idx + 1]
        curve = Curves.sine if upper > lower else Curves.isine
        return remap(curve(interop_x), 0, 1, lower, upper)

    def on_run(self):
        self.power = self.get_value()


class Generation(SubsystemWithProfile):
    profile_base_multiplier_field_name = "installed_capacity"

    def __init__(self, **kwargs) -> None:
        self.primary_energy = str(kwargs.get("primary_energy"))
        self.conversion_technique = str(kwargs.get("conversion_technique"))
        self.installed_capacity = float(kwargs.get("installed_capacity"))
        super().__init__(**kwargs)


class Consumption(SubsystemWithProfile):
    profile_base_multiplier_field_name = "peak_demand"

    def __init__(self, **kwargs) -> None:
        self.peak_demand = float(kwargs.get("peak_demand"))
        super().__init__(**kwargs)


class Storage(SubsystemBase):
    def __init__(self, **kwargs) -> None:
        self.technology = str(kwargs.get("technology"))
        self.max_capacity = float(kwargs.get("max_capacity"))
        self.usable_capacity = float(kwargs.get("usable_capacity"))
        super().__init__(**kwargs)

    def on_run(self):
        pass


class InterconnectedSubsystem(SubsystemBase):

    subsystem_reporting_enabled: Final = True

    def __init__(
        self,
        consumptions: list[Consumption],
        generations: list[Generation],
        storages: list[Storage],
        set_states: Callable,
        subsystem_reporting=subsystem_reporting_enabled,
        **kwargs,
    ) -> None:
        self.consumptions = consumptions
        self.generations = generations
        self.storages = storages
        self.set_states = set_states
        self.total_consumption = 0.0
        self.total_generation = 0.0
        self.subsystem_reporting_enabled = subsystem_reporting
        super().__init__(**kwargs)

    def get_generation_states(self) -> dict[str, any]:
        result = {}
        total_power = 0.0
        for gen in self.generations:
            total_power += gen.power
            result.update({f"{gen.id_}/power": gen.power})
        self.total_generation = total_power
        return result

    def get_consumption_states(self) -> dict[str, any]:
        result = {}
        total_power = 0.0
        for gen in self.consumptions:
            total_power += gen.power
            result.update({f"{gen.id_}/power": gen.power})
        self.total_consumption = total_power
        return result

    def get_storage_states(self) -> dict[str, any]:
        return {}

    @property
    def self_consumption(self):
        return min(self.total_generation, self.total_consumption)

    @property
    def import_export_status(self):
        if self.self_consumption < self.total_generation:
            return ProsumerStatus.EXPORT
        if self.self_consumption < self.total_consumption:
            return ProsumerStatus.IMPORT
        return ProsumerStatus.SELF_SUSTAIN

    @property
    def export_power(self):
        return self.total_generation - self.total_consumption

    @states_setter
    def on_run(self) -> dict[str, any]:
        generation_states = self.get_generation_states()
        consumption_states = self.get_consumption_states()
        # TODO: update self.total_consumption with storage charge rate if charging

        states = {}

        if self.subsystem_reporting_enabled:
            states.update(
                generations=generation_states,
                consumptions=consumption_states,
                # TODO: include storage system
            )

        states.update(
            generation=self.total_generation,
            consumption=self.total_consumption,
            self_consumption=self.self_consumption,
            net_export=self.export_power,
            status=self.import_export_status.value,
            last_updated_at=datetime.now(),
        )

        return states
