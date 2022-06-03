from datetime import datetime
from functools import cached_property
from random import uniform
from typing import Callable, Final
from utils.utils import Base
from utils.decorators import setInterval
from utils.mixins import StateEntityMixin
from utils.interpolate import Curves, remap


class SubsystemBase(StateEntityMixin, Base):
    """
    Base class for a subsystem.
    """

    auto_start = True
    run_interval = 5

    config: dict
    states_setter: Callable

    @cached_property
    def entity_name(self):
        """
        The plural name of the entity with subsystem id.
        """
        return f"{super().entity_name}/{self.config['id']}"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.runner: any = None
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
    profile_base_multiplier: float
    profile_multiplier_config_name: str

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.compiled_profile = self.generate_profile()

    def generate_profile(self) -> list:
        """
        Attempts to parse profile from `self.config` and generates profile
        between `r0` and `r1` bounds for `7 days`
        """
        profile, result = self.config["profile"], []
        if profile["source"] == "range_30m":
            self.profile_base_multiplier = float(
                self.config[self.profile_multiplier_config_name]
            )
            self.profile_interval = _RANGE_30M
            p_bounds = zip(profile["r0"], profile["r1"])
            for _ in range(7):
                result += [uniform(*i) for i in p_bounds]
        return result

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
        return (
            remap(curve(interop_x), 0, 1, lower, upper) * self.profile_base_multiplier
        )

    def on_run(self):
        self.set_states(
            {
                "power": self.get_value(),
            }
        )


class Generation(SubsystemWithProfile):
    profile_multiplier_config_name = "installedCapacity"


class Consumption(SubsystemWithProfile):
    profile_multiplier_config_name = "peakDemand"


class Storage(SubsystemBase):
    def on_run(self):
        pass
