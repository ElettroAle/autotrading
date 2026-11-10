from decimal import Decimal

from pydantic import BaseModel

from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.step_outcome import StepOutcome
from autotrading.domain.verification.verification_run import VerificationRun


def _text(amount: Decimal) -> str:
    # Amounts travel as strings, so no precision is lost on the way (ADR 0018).
    return str(amount)


class PositionReadingResponse(BaseModel):
    coin: str
    side: str
    size: str
    leverage: int

    @classmethod
    def of(cls, position: PositionReading) -> PositionReadingResponse:
        return cls(coin=position.coin, side=position.side, size=_text(position.size), leverage=position.leverage)


class AccountReadingResponse(BaseModel):
    balance: str
    available_margin: str
    currency: str
    positions: list[PositionReadingResponse]

    @classmethod
    def of(cls, reading: AccountReading) -> AccountReadingResponse:
        return cls(
            balance=_text(reading.balance),
            available_margin=_text(reading.available_margin),
            currency=reading.currency,
            positions=[PositionReadingResponse.of(position) for position in reading.positions],
        )


class OrderResultResponse(BaseModel):
    succeeded: bool
    fee: str
    realized_pnl: str
    message: str | None

    @classmethod
    def of(cls, result: OrderResult) -> OrderResultResponse:
        return cls(
            succeeded=result.succeeded,
            fee=_text(result.fee),
            realized_pnl=_text(result.realized_pnl),
            message=result.message,
        )


class StepOutcomeResponse(BaseModel):
    step: str
    succeeded: bool
    message: str | None
    reading: AccountReadingResponse | None
    order: OrderResultResponse | None

    @classmethod
    def of(cls, outcome: StepOutcome) -> StepOutcomeResponse:
        return cls(
            step=outcome.step.value,
            succeeded=outcome.succeeded,
            message=outcome.message,
            reading=None if outcome.reading is None else AccountReadingResponse.of(outcome.reading),
            order=None if outcome.order is None else OrderResultResponse.of(outcome.order),
        )


class VerificationRunResponse(BaseModel):
    """A run of the procedure with the outcome of each step: the same body from worker and API (ADR 0024)."""

    id: str
    account_id: str
    user_id: str
    environment: str
    started_at: str
    outcome: str
    total_fee: str
    realized_pnl: str
    warning: str | None
    steps: list[StepOutcomeResponse]

    @classmethod
    def of(cls, run: VerificationRun) -> VerificationRunResponse:
        return cls(
            id=str(run.id),
            account_id=str(run.account_id),
            user_id=run.user_id,
            environment=run.environment,
            started_at=run.started_at.isoformat(),
            outcome=run.outcome,
            total_fee=_text(run.total_fee),
            realized_pnl=_text(run.realized_pnl),
            warning=run.warning,
            steps=[StepOutcomeResponse.of(outcome) for outcome in run.steps],
        )
