from decimal import Decimal

from pydantic import BaseModel

from autotrading.domain.orders.order_outcome import OrderOutcome


def _text(amount: Decimal | None) -> str | None:
    # Amounts travel as strings, so no precision is lost on the way (ADR 0018).
    return None if amount is None else str(amount)


class OrderOutcomeResponse(BaseModel):
    """The outcome of an order as the exchange gave it: the same body from worker and API (ADR 0023)."""

    order_id: str
    status: str
    coin: str
    filled_size: str | None
    average_price: str | None
    fee: str | None
    realized_pnl: str | None
    executed_at: str | None
    reason: str | None
    exchange_message: str | None

    @classmethod
    def of(cls, outcome: OrderOutcome) -> OrderOutcomeResponse:
        return cls(
            order_id=str(outcome.order_id),
            status=outcome.status.value,
            coin=outcome.coin,
            filled_size=_text(outcome.filled_size),
            average_price=_text(outcome.average_price),
            fee=_text(outcome.fee),
            realized_pnl=_text(outcome.realized_pnl),
            executed_at=None if outcome.executed_at is None else outcome.executed_at.isoformat(),
            reason=None if outcome.reason is None else outcome.reason.value,
            exchange_message=outcome.exchange_message,
        )
