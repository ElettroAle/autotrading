"""Readings, order results and runs of the procedure of verification, as the tests build them."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Step
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.step_outcome import StepOutcome
from autotrading.domain.verification.verification_run import VerificationRun

STARTED_AT = datetime(2026, 11, 10, 11, 59, 59, tzinfo=UTC)
LONG_BTC = PositionReading("BTC", "long", Decimal("0.00012"), 2)
SHORT_ETH = PositionReading("ETH", "short", Decimal("1.5"), 3)
OPENED = OrderResult(succeeded=True, fee=Decimal("0.0054"), realized_pnl=Decimal(0))
CLOSED = OrderResult(succeeded=True, fee=Decimal("0.0055"), realized_pnl=Decimal("-0.012"))
REFUSED = OrderResult(succeeded=False, message="Insufficient margin to place order. asset=0")


def a_reading(*positions: PositionReading, margin: Decimal = Decimal(100)) -> AccountReading:
    return AccountReading(Decimal("250.5"), margin, "USDC", positions)


def a_run(*steps: StepOutcome) -> VerificationRun:
    return VerificationRun(uuid4(), uuid4(), "oid-anna", "dev", STARTED_AT, steps)


def passed_steps() -> tuple[StepOutcome, ...]:
    return (
        StepOutcome(Step.OPENING, succeeded=True, order=OPENED),
        StepOutcome(Step.READING_AFTER_OPENING, succeeded=True, reading=a_reading(LONG_BTC)),
        StepOutcome(Step.CLOSING, succeeded=True, order=CLOSED),
        StepOutcome(Step.READING_AFTER_CLOSING, succeeded=True, reading=a_reading()),
    )
