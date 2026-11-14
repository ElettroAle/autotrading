from pydantic import BaseModel

from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition, BalanceMovement


class ActivityPositionResponse(BaseModel):
    # Amounts travel as strings, so no precision is lost on the way (ADR 0018).
    asset: str
    side: str
    size: str
    margin: str
    unrealized_pnl: str
    leverage: int
    entry_price: str

    @classmethod
    def of(cls, position: AccountPosition) -> ActivityPositionResponse:
        return cls(
            asset=position.asset,
            side=position.side.value,
            size=str(position.size),
            margin=str(position.margin),
            unrealized_pnl=str(position.unrealized_pnl),
            leverage=position.leverage,
            entry_price=str(position.entry_price),
        )


class ActivityMovementResponse(BaseModel):
    movement_id: str
    amount: str
    moved_at: str

    @classmethod
    def of(cls, movement: BalanceMovement) -> ActivityMovementResponse:
        return cls(
            movement_id=movement.movement_id, amount=str(movement.amount), moved_at=movement.moved_at.isoformat()
        )


class AccountActivityResponse(BaseModel):
    """What the exchange shows of an account, from the worker to the API for the state of its flows (R1.6.1)."""

    currency: str
    balance: str
    available_margin: str
    positions: list[ActivityPositionResponse]
    movements: list[ActivityMovementResponse]
    read_at: str

    @classmethod
    def of(cls, activity: AccountActivity) -> AccountActivityResponse:
        return cls(
            currency=activity.currency,
            balance=str(activity.balance),
            available_margin=str(activity.available_margin),
            positions=[ActivityPositionResponse.of(position) for position in activity.positions],
            movements=[ActivityMovementResponse.of(movement) for movement in activity.movements],
            read_at=activity.read_at.isoformat(),
        )
