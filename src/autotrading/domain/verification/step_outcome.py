from dataclasses import dataclass

from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Step
from autotrading.domain.verification.reading import AccountReading


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """The outcome of one step, recorded also when the step fails (R0.4.1)."""

    step: Step
    succeeded: bool
    message: str | None = None
    reading: AccountReading | None = None
    order: OrderResult | None = None
