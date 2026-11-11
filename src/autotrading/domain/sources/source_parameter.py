from dataclasses import dataclass

from autotrading.domain.sources.errors import InvalidSourceParameterError


@dataclass(frozen=True, slots=True)
class SourceParameter:
    """A whole-number setting of a source, with the value a flow gets when it says nothing (R1.3.1, R1.3.2)."""

    key: str
    label: str
    default: int
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if not self.minimum <= self.default <= self.maximum:
            raise InvalidSourceParameterError(self.key)

    def accepts(self, value: int) -> bool:
        return self.minimum <= value <= self.maximum
