from pydantic import BaseModel

from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.position import Position


class AmountResponse(BaseModel):
    # Amounts travel as strings, so no precision is lost on the way (ADR 0018).
    amount: str
    currency: str

    @classmethod
    def of(cls, balance: Balance) -> AmountResponse:
        return cls(amount=str(balance.amount), currency=balance.currency)


class PositionResponse(BaseModel):
    coin: str
    side: str
    size: str
    leverage: int
    entry_price: str
    unrealized_pnl: str
    liquidation_price: str | None

    @classmethod
    def of(cls, position: Position) -> PositionResponse:
        liquidation = position.liquidation_price
        return cls(
            coin=position.coin,
            side=position.side.value,
            size=str(position.size),
            leverage=position.leverage,
            entry_price=str(position.entry_price),
            unrealized_pnl=str(position.unrealized_pnl),
            liquidation_price=None if liquidation is None else str(liquidation),
        )


class AccountStateResponse(BaseModel):
    """The state of an account read from the exchange at the request (R0.2.2): the same body from worker and API."""

    balance: AmountResponse
    available_margin: AmountResponse
    positions: list[PositionResponse]
    read_at: str

    @classmethod
    def of(cls, state: AccountState) -> AccountStateResponse:
        return cls(
            balance=AmountResponse.of(state.balance),
            available_margin=AmountResponse.of(state.available_margin),
            positions=[PositionResponse.of(position) for position in state.positions],
            read_at=state.read_at.isoformat(),
        )
