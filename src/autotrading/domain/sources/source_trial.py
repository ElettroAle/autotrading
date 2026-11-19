from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from autotrading.domain.sources.errors import InvalidSourceTrialError
from autotrading.domain.sources.source_sample import SourceValue


class TrialOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SourceTrial:
    """What one adapter of a source answered a trial: the values it read, or the reason it read none and whether that
    reason repeats until the user acts, as in a cycle (R1.2.5, R6.3.1). Nothing of a trial is ever recorded.
    """

    outcome: TrialOutcome
    values: tuple[SourceValue, ...]
    response_milliseconds: int
    reason: str | None = None
    permanent: bool = False

    def __post_init__(self) -> None:
        failed = self.outcome is TrialOutcome.FAILED
        if self.response_milliseconds < 0 or failed != (self.reason is not None) or (failed and self.values):
            raise InvalidSourceTrialError

    @classmethod
    def succeeded(cls, values: tuple[SourceValue, ...], response_milliseconds: int) -> SourceTrial:
        return cls(TrialOutcome.SUCCEEDED, values, response_milliseconds)

    @classmethod
    def failed(cls, reason: str, permanent: bool, response_milliseconds: int) -> SourceTrial:
        return cls(TrialOutcome.FAILED, (), response_milliseconds, reason, permanent)

    @property
    def data_at(self) -> datetime | None:
        """The instant of the newest value read, none when the adapter read nothing."""
        return max((value.reference_at for value in self.values), default=None)
