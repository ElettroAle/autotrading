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
