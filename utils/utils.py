def acclimate_dict_for_kwargs(source: dict[str, any]) -> dict[str, any]:
    return {
        k.removeprefix("$"): (
            acclimate_dict_for_kwargs(v) if isinstance(v, dict) else v
        )
        for k, v in source.items()
    }


class Base:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)
