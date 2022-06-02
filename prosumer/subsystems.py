from datetime import datetime
from functools import cached_property
from random import uniform
from typing import Callable
from utils.utils import Base
from utils.decorators import setInterval
from utils.mixins import StateEntityMixin


class SubsystemBase(StateEntityMixin, Base):
    """
    Base class for a subsystem.
    """

    auto_start = True
    run_interval = 1

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
        self.runner = self.run()
        self.started_at = datetime.now()

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


class SubsystemWithProfile(SubsystemBase):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.compiled_profile = self.generate_profile()

    def on_run(self):
        self.set_states(
            {
                "now": datetime.now(),
            }
        )

    def generate_profile(self) -> list:
        """
        Attempts to parse profile from `self.config` and generates profile
        between `r0` and `r1` bounds for `7 days`
        """
        profile, result = self.config["profile"], []
        if profile["source"] == "range_30m":
            p_bounds = zip(profile["r0"], profile["r1"])
            for _ in range(7):
                result += [uniform(*i) for i in p_bounds]
        return result


class Generation(SubsystemWithProfile):
    pass


class Consumption(SubsystemWithProfile):
    pass


class Storage(SubsystemBase):
    def on_run(self):
        pass
