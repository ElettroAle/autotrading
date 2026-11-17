from datetime import datetime

from pydantic import BaseModel

from autotrading.domain.flows.openings_suspension import OpeningsSuspension, OpeningsSuspensionCause


class OpeningsSuspensionResponse(BaseModel):
    """The openings of a flow suspended: the reason, since when, the cause and whether the user resumes them from the
    flow, true only after a maximum loss (R3.2.2, R3.3.1).
    """

    reason: str
    suspended_at: datetime
    cause: OpeningsSuspensionCause
    resumable: bool

    @classmethod
    def of(cls, suspension: OpeningsSuspension | None) -> OpeningsSuspensionResponse | None:
        if suspension is None:
            return None
        return cls(
            reason=suspension.reason,
            suspended_at=suspension.suspended_at,
            cause=suspension.cause,
            resumable=suspension.resumable,
        )
