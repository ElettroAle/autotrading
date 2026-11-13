from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import NotRequired, TypedDict, cast


class _Leverage(TypedDict):
    value: int


class _PositionEntry(TypedDict):
    coin: str
    szi: str
    leverage: _Leverage
    entryPx: str
    unrealizedPnl: str
    marginUsed: str
    liquidationPx: NotRequired[str | None]


class _AssetPosition(TypedDict):
    position: _PositionEntry


class _MarginSummary(TypedDict):
    accountValue: str


class _ClearinghouseState(TypedDict):
    """The clearinghouse state as Hyperliquid answers it; a wrong shape fails while it is read."""

    marginSummary: _MarginSummary
    withdrawable: str
    assetPositions: list[_AssetPosition]
    time: int


@dataclass(frozen=True, slots=True)
class _UserPosition:
    """One position of the clearinghouse state, as the exchange gives it: the size is signed, long above zero."""

    coin: str
    signed_size: Decimal
    leverage: int
    entry_price: Decimal
    unrealized_pnl: Decimal
    margin: Decimal
    liquidation_price: Decimal | None


@dataclass(frozen=True, slots=True)
class _UserState:
    """The clearinghouse state of an account, read once for every adapter that needs it."""

    account_value: Decimal
    withdrawable: Decimal
    positions: tuple[_UserPosition, ...]
    read_at: datetime


def user_state_of(answer: object) -> _UserState:
    """Raises KeyError, TypeError, ValueError or InvalidOperation on an answer of unexpected shape."""
    state = cast("_ClearinghouseState", answer)
    return _UserState(
        account_value=decimal_of(state["marginSummary"]["accountValue"]),
        withdrawable=decimal_of(state["withdrawable"]),
        positions=tuple(_position_of(entry["position"]) for entry in state["assetPositions"]),
        read_at=datetime.fromtimestamp(int(state["time"]) / 1000, UTC),
    )


def decimal_of(value: object) -> Decimal:
    return Decimal(str(value))


def _position_of(position: _PositionEntry) -> _UserPosition:
    liquidation = position.get("liquidationPx")
    return _UserPosition(
        coin=str(position["coin"]),
        signed_size=decimal_of(position["szi"]),
        leverage=int(position["leverage"]["value"]),
        entry_price=decimal_of(position["entryPx"]),
        unrealized_pnl=decimal_of(position["unrealizedPnl"]),
        margin=decimal_of(position["marginUsed"]),
        liquidation_price=None if liquidation is None else decimal_of(liquidation),
    )
