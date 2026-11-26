from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.domain.sources.errors import (
    InvalidSourceParameterError,
    SourceListValueOutOfRangeError,
    TooManySourceListValuesError,
)
from autotrading.domain.sources.source_parameter import SourceParameter, SourceParameterValue

# A list keeps at most this many values, so that a flow cannot make the exchange read and compute out of measure.
MAXIMUM_VALUES = 8
# The safety cap of every value, not a limit of the history of a market: what the history lacks is declared.
MAXIMUM_CANDLES = 10000
MAXIMUM_DAYS = 3650


@dataclass(frozen=True, slots=True)
class SourceListParameter:
    """A setting of a source that is a list of whole numbers, each one a period, a horizon or a window that produces
    its own values; an empty list switches them off (ADR parametri-delle-fonti-come-liste-libere).

    The catalog, the check of the flow, the API and the dashboard derive everything from this declaration.
    """

    key: str
    label: str
    default: tuple[int, ...]
    minimum: int
    maximum: int
    maximum_values: int = MAXIMUM_VALUES
    # The words of the refusal of a value out of the range, when the requirement fixes them (R5.5.4).
    range_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.minimum <= self.maximum or self.maximum_values < 1:
            raise InvalidSourceParameterError(self.key)
        if self.default != _sorted_once(self.default) or len(self.default) > self.maximum_values:
            raise InvalidSourceParameterError(self.key)
        if any(not self.minimum <= value <= self.maximum for value in self.default):
            raise InvalidSourceParameterError(self.key)

    def accepted(self, value: object) -> tuple[int, ...]:
        """The list a flow asked for, ordered and without repetitions, when every value is in range and they are not
        too many; the refusal names the range or the maximum number of values.
        """
        if not isinstance(value, list | tuple) or not all(self._in_range(each) for each in value):
            raise SourceListValueOutOfRangeError(self.label, self.minimum, self.maximum, self.key, self.range_reason)
        values = _sorted_once(tuple(int(each) for each in value))
        if len(values) > self.maximum_values:
            raise TooManySourceListValuesError(self.label, self.maximum_values, self.key)
        return values

    def value_in(self, settings: Mapping[str, SourceParameterValue]) -> tuple[int, ...]:
        """The list of the flow among its settings, the default when it set none."""
        return self.accepted(settings.get(self.key, self.default))

    def _in_range(self, value: object) -> bool:
        # A boolean is an int in Python, never a number a user meant.
        return not isinstance(value, bool) and isinstance(value, int) and self.minimum <= value <= self.maximum


# Every parameter a source may declare.
type DeclaredParameter = SourceParameter | SourceListParameter


def _sorted_once(values: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(set(values)))
