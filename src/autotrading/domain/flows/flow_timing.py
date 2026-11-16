from dataclasses import dataclass
from datetime import datetime

from autotrading.domain.flows.openings_suspension import NOT_SUSPENDED, OpeningsStatus


@dataclass(frozen=True, slots=True)
class FlowTiming:
    """When the flow last started or resumed, why it paused on its own, if it did, when it first started and its
    openings suspended for maximum loss, if they are.

    The anchor plans the cycles (R1.2.1, R1.2.4); the first start is the beginning of the flow (ADR 0069); the openings
    are saved beside the flow (R3.2.2).
    """

    anchor: datetime | None
    pause_reason: str | None
    first_start: datetime | None = None
    openings: OpeningsStatus = NOT_SUSPENDED

    def beginning(self, anchor: datetime) -> datetime:
        """The first start of the flow, the beginning its return counts from (ADR 0069); a flow the database has not
        stamped yet started at the anchor of its cycles.
        """
        if self.first_start is None:
            return anchor
        return self.first_start


# A flow the database has not stamped yet: no anchor, no reason for a pause, no first start.
UNSTAMPED = FlowTiming(None, None)
