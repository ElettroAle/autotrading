from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FlowTiming:
    """When the flow last started or resumed, why it paused on its own, if it did, and when it first started.

    The anchor plans the cycles (R1.2.1, R1.2.4); the first start is the beginning of the flow (ADR 0069).
    """

    anchor: datetime | None
    pause_reason: str | None
    first_start: datetime | None = None


def flow_beginning(timing: FlowTiming | None, anchor: datetime) -> datetime:
    """The first start of the flow, the beginning its return counts from (ADR 0069); a flow the database has not
    stamped yet started at the anchor of its cycles.
    """
    if timing is None or timing.first_start is None:
        return anchor
    return timing.first_start
