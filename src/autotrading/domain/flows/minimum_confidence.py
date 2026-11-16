from dataclasses import dataclass

from autotrading.domain.flows.errors import InvalidMinimumConfidenceError

LOWEST_MINIMUM_CONFIDENCE, HIGHEST_MINIMUM_CONFIDENCE = 0, 100


@dataclass(frozen=True, slots=True)
class MinimumConfidence:
    """The confidence an opening of the flow needs at least, a whole number from 0 to 100 (R3.1.4).

    Only openings answer to it: closes and updates of the exit plan reduce the risk, so they always go on.
    """

    value: int

    def __post_init__(self) -> None:
        if not LOWEST_MINIMUM_CONFIDENCE <= self.value <= HIGHEST_MINIMUM_CONFIDENCE:
            raise InvalidMinimumConfidenceError

    @classmethod
    def optional(cls, value: int | None) -> MinimumConfidence | None:
        """The minimum the user gave; none when the flow has no minimum."""
        return None if value is None else cls(value)

    def admits(self, confidence: int) -> bool:
        return confidence >= self.value

    def __str__(self) -> str:
        return str(self.value)
