from dataclasses import dataclass

from autotrading.domain.sources.errors import (
    InvalidSourceParameterError,
    SourceParameterNotAmongChoicesError,
    SourceParameterOutOfRangeError,
)


@dataclass(frozen=True, slots=True)
class ParameterChoice:
    """A value a parameter admits, with the name a user knows it by (ADR orizzonti-lunghi-del-forecast)."""

    value: int
    label: str


@dataclass(frozen=True, slots=True)
class SourceParameter:
    """A whole-number setting of a source, with the value a flow gets when it says nothing (R1.3.1, R1.3.2).

    A parameter with choices admits only their values; one without admits every value of its range.
    """

    key: str
    label: str
    default: int
    minimum: int
    maximum: int
    choices: tuple[ParameterChoice, ...] = ()

    def __post_init__(self) -> None:
        if not self.minimum <= self.default <= self.maximum:
            raise InvalidSourceParameterError(self.key)
        if self.choices and self.default not in self._values:
            raise InvalidSourceParameterError(self.key)

    @classmethod
    def of_choices(cls, key: str, label: str, *, default: int, choices: tuple[ParameterChoice, ...]) -> SourceParameter:
        """A parameter that admits only the values of its choices, from the lowest to the highest."""
        if not choices:
            raise InvalidSourceParameterError(key)
        values = [choice.value for choice in choices]
        return cls(key, label, default, min(values), max(values), choices)

    @property
    def choice_labels(self) -> tuple[str, ...]:
        return tuple(choice.label for choice in self.choices)

    def accepts(self, value: int) -> bool:
        if self.choices:
            return value in self._values
        return self.minimum <= value <= self.maximum

    def accepted(self, value: object) -> int:
        """The value a flow asked for, when the parameter admits it; the refusal names what it admits."""
        # A boolean is an int in Python, never a number a user meant.
        if not isinstance(value, bool) and isinstance(value, int) and self.accepts(value):
            return value
        if self.choices:
            raise SourceParameterNotAmongChoicesError(self.label, self.choice_labels, self.key)
        raise SourceParameterOutOfRangeError(self.label, self.minimum, self.maximum, self.key)

    @property
    def _values(self) -> tuple[int, ...]:
        return tuple(choice.value for choice in self.choices)
