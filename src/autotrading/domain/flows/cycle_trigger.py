from enum import StrEnum


class CycleTrigger(StrEnum):
    """What started a cycle: its schedule (R1.2.1) or the user, who asked for it now (R6.5.2)."""

    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"
