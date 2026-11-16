from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExitPlan:
    """How the agent means to leave a position it opens: target price, stop price and the condition that invalidates
    the idea, each optional (R3.1.1, RF-17.05).
    """

    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None


@dataclass(frozen=True, slots=True)
class ExitPlanChange:
    """How the agent changes the plan of a position already open: a new target, stop or invalidation, each optional
    (none keeps the one in force), or the target removed. The stop is never removed (R3.1.3).
    """

    target: Decimal | None = None
    stop: Decimal | None = None
    invalidation: str | None = None
    remove_target: bool = False
