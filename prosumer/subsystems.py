from datetime import datetime
from functools import cached_property, reduce
from random import uniform
from typing import Callable, Final, Optional

from utils.decorators import setInterval
from utils.interpolate import Curves, remap
from utils.mixins import states_setter
from utils.utils import Base

from prosumer.enums import ProsumerStatus
from prosumer.mixins import SupportsExport


class SubsystemBase(Base):
    """
    Base class for a subsystem.
    """

    run_interval = 1
    auto_start = True
    timeseries_fields: tuple[str] = ()
    moving_avg_periods: tuple[int] = ()
    auto_invoke_get_states = False

    def __init__(self, **kwargs) -> None:
        self.id_ = str(kwargs.pop("id"))
        self.auto_start = bool(kwargs.pop("auto_start", SubsystemBase.auto_start))
        self.asset_value: Optional[float] = kwargs.pop("asset_value", None)
        self.runner: any = None
        self.moving_avg_periods = tuple(kwargs.pop("moving_avg_periods", []))

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
        self.update_timeseries_fields()
        if self.auto_invoke_get_states:
            self.get_states()

    def on_run(self):
        raise NotImplementedError("run")

    def _ensure_timeseries_samples_fields_initialized(self):
        # Initialize if does not exists...
        # TODO: improve this checking logic...
        # TODO: This heavy one time operation is being run unnecessarily every run_interval!
        for period in self.moving_avg_periods:
            for field in self.timeseries_fields:
                key = f"{field}_{period}m_samples"
                if key not in self.__dict__.keys():
                    setattr(self, key, [])

    def update_timeseries_fields(self):
        self._ensure_timeseries_samples_fields_initialized()
        for period in self.moving_avg_periods:
            for field in self.timeseries_fields:
                key = f"{field}_{period}m"
                present_value = getattr(self, field)
                max_samples = period * 60 // self.run_interval
                samples = list(getattr(self, key + "_samples"))
                samples.insert(0, present_value)
                if len(samples) == max_samples:
                    samples.pop()
                setattr(self, key + "_samples", samples)
                setattr(self, key, sum(samples) / len(samples))

    def register_timeseries_fields(self, *args):
        self.timeseries_fields += tuple([*args])

    def _get_timeseries_field_values(self, field: str):
        if field not in self.timeseries_fields:
            raise KeyError(field)
        field_values = {}
        for period in self.moving_avg_periods:
            key = f"{field}_{period}m"
            field_values.update({key: getattr(self, key)})
        return field_values

    def get_states(self) -> dict[str, any]:
        states = {}
        for field in self.timeseries_fields:
            states.update(
                {
                    field: getattr(self, field),
                    **self._get_timeseries_field_values(field),
                }
            )
        return states


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


class Generation(SupportsExport, SubsystemWithProfile):
    profile_base_multiplier_field_name = "installed_capacity"

    def __init__(self, **kwargs) -> None:
        self.primary_energy = str(kwargs.get("primary_energy"))
        self.conversion_technique = str(kwargs.get("conversion_technique"))
        self.installed_capacity = float(kwargs.get("installed_capacity"))
        self.register_timeseries_fields("power")
        super().__init__(**kwargs)


class Consumption(SubsystemWithProfile):
    profile_base_multiplier_field_name = "peak_demand"

    def __init__(self, **kwargs) -> None:
        self.peak_demand = float(kwargs.get("peak_demand"))
        self.register_timeseries_fields("power")
        super().__init__(**kwargs)


class Storage(SupportsExport, SubsystemBase):
    def __init__(self, **kwargs) -> None:
        self.technology = str(kwargs.get("technology"))
        self.max_capacity = float(kwargs.get("max_capacity"))
        self.usable_capacity = float(kwargs.get("usable_capacity"))
        self.max_charge_rate = float(kwargs.get("max_charge_rate"))
        self.max_discharge_rate = float(
            kwargs.get("max_discharge_rate", self.max_charge_rate)
        )
        self.charge_efficiency = float(kwargs.get("charge_efficiency", 0.9))
        self.discharge_efficiency = float(kwargs.get("discharge_efficiency", 0.9))
        super().__init__(**kwargs)

    def on_run(self):
        pass


class InterconnectedSubsystem(SupportsExport, SubsystemBase):

    auto_invoke_get_states = True

    def __init__(
        self,
        consumptions: list[Consumption],
        generations: list[Generation],
        storages: list[Storage],
        set_states: Callable,
        subsystem_reporting: tuple[str],
        **kwargs,
    ) -> None:
        self.consumptions = consumptions
        self.generations = generations
        self.storages = storages
        self.set_states = set_states
        self.total_consumption = 0.0
        self.total_generation = 0.0
        self.subsystem_reporting = subsystem_reporting
        unit_export_price = (
            self.generations_weighted_unit_export_price
            + self.storages_weighted_unit_export_price
        )
        super().__init__(can_export=True, unit_export_price=unit_export_price, **kwargs)

    @cached_property
    def generations_weighted_unit_export_price(self):
        installed_capacity, wavg_num = 0, 0
        for sys in filter(lambda x: x.export_allowed, self.generations):
            installed_capacity += sys.installed_capacity
            wavg_num += sys.installed_capacity * sys.unit_export_price
        return wavg_num / installed_capacity

    @cached_property
    def storages_weighted_unit_export_price(self):
        # TODO: [Storage] Not Implemented
        return 0

    @staticmethod
    def _system_states_and_power_reducer(acc, sys: SubsystemBase):
        acc[0].update({sys.id_: sys.get_states()})
        return acc[0], acc[1] + sys.power

    def get_generation_states(self) -> dict[str, any]:
        reducer = self._system_states_and_power_reducer
        states, self.total_generation = reduce(reducer, self.generations, ({}, 0))
        return states

    def get_consumption_states(self) -> dict[str, any]:
        reducer = self._system_states_and_power_reducer
        states, self.total_consumption = reduce(reducer, self.consumptions, ({}, 0))
        return states

    def get_storage_states(self) -> dict[str, any]:
        raise NotImplementedError()

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
    def net_export_power(self):
        return self.total_generation - self.total_consumption

    @states_setter
    def on_run(self) -> dict[str, any]:
        generation_states = self.get_generation_states()
        consumption_states = self.get_consumption_states()
        # TODO: update self.total_consumption with storage charge rate if charging

        states = {}

        if "generation" in self.subsystem_reporting:
            states.update(generations=generation_states)
        if "consumption" in self.subsystem_reporting:
            states.update(consumptions=consumption_states)
        # TODO: include storage system

        states.update(
            generation=self.total_generation,
            consumption=self.total_consumption,
            self_consumption=self.self_consumption,
            net_export=self.net_export_power,
            status=self.import_export_status.value,
            export_price=self.unit_export_price,
            last_updated_at=datetime.now(),
        )

        return states
