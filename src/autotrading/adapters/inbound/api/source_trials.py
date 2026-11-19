from datetime import datetime

from pydantic import BaseModel, Field

from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.source_trial import SourceTrial, TrialOutcome


class SourceTrialRequest(BaseModel):
    """The asset, only for a per-asset source, and the parameters the user set: the others take their default."""

    asset: str | None = None
    parameters: dict[str, int] = Field(default_factory=dict)


class SourceTrialValueResponse(BaseModel):
    reference_at: datetime
    values: dict[str, str]

    @classmethod
    def of(cls, value: SourceValue) -> SourceTrialValueResponse:
        return cls(reference_at=value.reference_at, values=dict(value.values))


class SourceTrialResponse(BaseModel):
    """What the adapter answered the trial: a source that fails is the outcome, not an error of the request (R6.3.1)."""

    outcome: TrialOutcome
    values: list[SourceTrialValueResponse]
    # The instant of the newest value read, none when the adapter read nothing.
    data_at: datetime | None
    response_milliseconds: int
    reason: str | None
    permanent: bool

    @classmethod
    def of(cls, trial: SourceTrial) -> SourceTrialResponse:
        return cls(
            outcome=trial.outcome,
            values=[SourceTrialValueResponse.of(value) for value in trial.values],
            data_at=trial.data_at,
            response_milliseconds=trial.response_milliseconds,
            reason=trial.reason,
            permanent=trial.permanent,
        )
