from functools import cached_property


class SupportsExport:
    def __init__(self, **kwargs) -> None:
        self.export_allowed = bool(kwargs.pop("can_export", True))
        self._unit_export_price = (
            float(kwargs.pop("export_price")) if self.export_allowed else None
        )
        super().__init__(**kwargs)

    @cached_property
    def export_price(self):
        if not self.export_allowed:
            raise PermissionError(
                "Not allowed to read unit_export_price as `export_allowed` is set to False"
            )
        return float(self._unit_export_price)
