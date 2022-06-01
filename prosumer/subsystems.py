import datetime
from django.utils.timezone import now
from random import uniform

from utils.decorators import setInterval


class _Subsystem:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.id = config["id"]
        self.started_at = now()


class _SubsystemWithProfile(_Subsystem):
    profile = []

    def generate_profile(self):
        profile = self.config["$profile"]
        if profile["source"] == "range_30m":
            profile_bounds = zip(profile["r0"], profile["r1"])
            for _ in range(7):
                self.profile += [uniform(*i) for i in profile_bounds]


class Generation(_SubsystemWithProfile):
    @setInterval(1)
    def run(self):
        print(datetime.datetime.now())

    def __init__(self, config: dict) -> None:
        self.run()
        super().__init__(config)


class Consumption(_SubsystemWithProfile):
    pass


class Storage(_Subsystem):
    pass
