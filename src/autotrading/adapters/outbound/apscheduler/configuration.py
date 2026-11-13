from dataclasses import dataclass
from datetime import UTC, tzinfo


@dataclass(frozen=True, slots=True)
class _ApSchedulerSettings:
    """How many cycles run at once, and the zone of the instants.

    The threads bound the cycles running together: one past them waits for a free thread and starts late, as its
    record says. The running jobs of one flow are not bounded by the scheduler: the cycle itself skips an instant
    whose flow is still held by the previous one, and records it (R1.2.2).
    """

    threads: int = 64
    running_per_flow: int = 64
    zone: tzinfo = UTC
