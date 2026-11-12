from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FlowTiming:
    """When the flow last started or resumed, and why it paused on its own, if it did (R1.2.1, R1.2.4)."""

    anchor: datetime | None
    pause_reason: str | None
