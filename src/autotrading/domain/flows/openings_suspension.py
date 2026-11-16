from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from autotrading.domain.flows.errors import OpeningsNotSuspendedError
from autotrading.domain.flows.openings_resume import OpeningsResume

ONE_DAY = timedelta(days=1)

# What a cycle records for an opening not executed while the openings are suspended for maximum loss (R3.2.2).
MAXIMUM_LOSS_BLOCK = "aperture sospese per perdita massima"


class OpeningsSuspensionCause(StrEnum):
    """Why the openings of a flow are suspended: a maximum loss passed (R3.2.2) or an alarm of reconciliation open on
    its account (R3.3.1). Only the first one the user resumes from the flow; the second ends with the confirmation of
    the account.
    """

    MAXIMUM_LOSS = "perdita_massima"
    RECONCILIATION = "riconciliazione"


def day_start(at: datetime) -> datetime:
    """00:00 UTC of the day of the instant: the daily loss counts from there (R3.2.2)."""
    return at.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass(frozen=True, slots=True)
class OpeningsSuspension:
    """The openings of a flow suspended: the reason, as the user reads it, since when, and the cause (R3.2.2, R3.3.1).

    One concept for every cause: the risk check blocks the openings, the API and the dashboard show it, the same way.
    """

    reason: str
    suspended_at: datetime
    cause: OpeningsSuspensionCause = OpeningsSuspensionCause.MAXIMUM_LOSS

    @property
    def resumable(self) -> bool:
        """Whether the user resumes the openings from the flow: only after a maximum loss."""
        return self.cause is OpeningsSuspensionCause.MAXIMUM_LOSS

    @property
    def blocked_reason(self) -> str:
        """What a cycle records for an opening it does not execute."""
        if self.cause is OpeningsSuspensionCause.MAXIMUM_LOSS:
            return MAXIMUM_LOSS_BLOCK
        return self.reason

    @staticmethod
    def first_of(*suspensions: OpeningsSuspension | None) -> OpeningsSuspension | None:
        """The suspension in force among the causes, the maximum loss first: the user can resume it at once."""
        return next((suspension for suspension in suspensions if suspension is not None), None)

    def ends_at(self, resume: OpeningsResume) -> datetime | None:
        """The instant the suspension ends on its own: 00:00 UTC of the next day, never with the manual resume."""
        if resume is OpeningsResume.MANUAL:
            return None
        return day_start(self.suspended_at) + ONE_DAY

    def in_force(self, at: datetime, resume: OpeningsResume) -> bool:
        ends_at = self.ends_at(resume)
        return ends_at is None or at < ends_at


@dataclass(frozen=True, slots=True)
class OpeningsStatus:
    """The openings of a flow as saved: the suspension, if one was saved, and the last resume.

    The resume the next day needs no write: the suspension read at an instant after its end is already lifted, and its
    end is the resume the peak counts from (ADR perdita-massima-sui-valori-di-equity-registrati).
    """

    suspension: OpeningsSuspension | None
    resumed_at: datetime | None

    def ended_at(self, instant: datetime, resume: OpeningsResume) -> datetime | None:
        """The end of a suspension that ended on its own by the instant, None for any other."""
        suspension = self.suspension
        if suspension is None or suspension.in_force(instant, resume):
            return None
        return suspension.ends_at(resume)

    def at(self, instant: datetime, resume: OpeningsResume) -> OpeningsStatus:
        """The openings as they stand at the instant, with a suspension ended on its own already lifted."""
        ended_at = self.ended_at(instant, resume)
        if ended_at is None:
            return self
        return OpeningsStatus(None, ended_at)

    def peak_since(self, first_start: datetime) -> datetime:
        """The peak counts from the first start of the flow or from the last resume of its openings, the later one."""
        if self.resumed_at is None:
            return first_start
        return max(first_start, self.resumed_at)

    def suspended(self, reason: str, at: datetime) -> OpeningsStatus:
        return replace(self, suspension=OpeningsSuspension(reason, at))

    def resumed(self, at: datetime, flow_name: str) -> OpeningsStatus:
        """The openings resumed by the user: the suspension is lifted and the peak counts again from now."""
        if self.suspension is None:
            raise OpeningsNotSuspendedError(flow_name)
        return replace(self, suspension=None, resumed_at=at)


# The openings of a flow nobody suspended or resumed yet.
NOT_SUSPENDED = OpeningsStatus(None, None)
