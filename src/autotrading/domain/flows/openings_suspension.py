from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from autotrading.domain.flows.errors import OpeningsNotSuspendedError
from autotrading.domain.flows.openings_resume import OpeningsResume

ONE_DAY = timedelta(days=1)


def day_start(at: datetime) -> datetime:
    """00:00 UTC of the day of the instant: the daily loss counts from there (R3.2.2)."""
    return at.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass(frozen=True, slots=True)
class OpeningsSuspension:
    """The openings of a flow suspended for maximum loss: the threshold passed, as the user reads it, and when
    (R3.2.2).
    """

    reason: str
    suspended_at: datetime

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
