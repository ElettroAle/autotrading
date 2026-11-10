from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.verification.procedure import PROCEDURE_OPENING, Step
from autotrading.domain.verification.step_outcome import StepOutcome

PASSED = "superata"


@dataclass(frozen=True, slots=True)
class VerificationRun:
    """A run of the procedure on an account of the tenant, with the outcome of each step it executed (R0.4.1)."""

    id: UUID
    account_id: UUID
    user_id: str
    environment: str
    started_at: datetime
    steps: tuple[StepOutcome, ...]

    @property
    def failed_step(self) -> Step | None:
        return next((outcome.step for outcome in self.steps if not outcome.succeeded), None)

    @property
    def outcome(self) -> str:
        failed = self.failed_step
        return PASSED if failed is None else f"fallita al passo {failed.short_name}"

    @property
    def total_fee(self) -> Decimal:
        return sum((outcome.order.fee for outcome in self.steps if outcome.order is not None), Decimal(0))

    @property
    def realized_pnl(self) -> Decimal:
        return sum((outcome.order.realized_pnl for outcome in self.steps if outcome.order is not None), Decimal(0))

    @property
    def warning(self) -> str | None:
        """Said when the procedure opened its position and did not close it: the account still holds it."""
        if self._succeeded(Step.OPENING) and not self._succeeded(Step.CLOSING):
            return f"sul conto resta aperta una posizione {PROCEDURE_OPENING.side} su {PROCEDURE_OPENING.coin}"
        return None

    def _succeeded(self, step: Step) -> bool:
        return any(outcome.step is step and outcome.succeeded for outcome in self.steps)
