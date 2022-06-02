import weakref
from collections import defaultdict
from functools import cached_property
from typing import Callable


class StateEntity:
    """
    Mixin that makes the instance a state entity. `states_setter` should be
    set before invoking `set_states`.
    """

    @cached_property
    def entity_name(self):
        """
        The plural name of the entity.
        """
        return type(self).__name__.lower() + "s"

    states_setter: Callable

    def set_states(self, states: dict[str, any], parent_state: str | None = None):
        """
        Updates the states using the provided `states_setter`.
        """
        resolved_pstate = (
            "/".join([self.entity_name, parent_state])
            if parent_state
            else self.entity_name
        )
        self.states_setter(states=states, parent_state=resolved_pstate)


class KeepRefs(object):
    __refs__ = defaultdict(list)

    def __init__(self):
        self.__refs__[self.__class__].append(weakref.ref(self))
        super().__init__()

    @classmethod
    def get_instances(cls):
        for inst_ref in cls.__refs__[cls]:
            inst = inst_ref()
            if inst is not None:
                yield inst
