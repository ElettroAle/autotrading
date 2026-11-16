from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import NotRequired, TypedDict, cast

# The modes whose balance is the one of the spot state, shared by spot and perps (Bug 392).
UNIFIED_MODES = frozenset({"unifiedAccount", "portfolioMargin"})
MARGIN_COIN = "USDC"
ISOLATED = "isolated"


class _Leverage(TypedDict):
    type: str
    value: int


class _PositionEntry(TypedDict):
    coin: str
    szi: str
    leverage: _Leverage
    entryPx: str
    positionValue: str
    unrealizedPnl: str
    marginUsed: str
    liquidationPx: NotRequired[str | None]


class _AssetPosition(TypedDict):
    position: _PositionEntry


class _MarginSummary(TypedDict):
    accountValue: str


class _SpotBalance(TypedDict):
    coin: str
    total: str
    hold: str


class _SpotState(TypedDict):
    balances: list[_SpotBalance]


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
    mark_price: Decimal
    unrealized_pnl: Decimal
    margin: Decimal
    liquidation_price: Decimal | None
    isolated: bool = False


@dataclass(frozen=True, slots=True)
class _UserState:
    """The clearinghouse state of an account, read once for every adapter that needs it."""

    account_value: Decimal
    withdrawable: Decimal
    positions: tuple[_UserPosition, ...]
    read_at: datetime


def user_state_of(answer: object) -> _UserState:
    """Raises KeyError, TypeError, ValueError or ArithmeticError on an answer of unexpected shape."""
    state = cast("_ClearinghouseState", answer)
    return _UserState(
        account_value=decimal_of(state["marginSummary"]["accountValue"]),
        withdrawable=decimal_of(state["withdrawable"]),
        positions=tuple(_position_of(entry["position"]) for entry in state["assetPositions"]),
        read_at=datetime.fromtimestamp(int(state["time"]) / 1000, UTC),
    )


def in_account_mode(perps: _UserState, mode: object, spot: object) -> _UserState:
    """The state with the balance of the account mode the exchange declares (Bug 392, ADR
    saldo-dalla-modalita-del-conto-hyperliquid). Under unified account and portfolio margin the USDC of the spot state
    is the balance of spot and perps: the open result adds to it, and what orders hold and isolated positions use is
    not available. Raises KeyError, TypeError, ValueError or ArithmeticError on a spot state of unexpected shape.
    """
    if mode not in UNIFIED_MODES:
        return perps
    usdc = next((balance for balance in cast("_SpotState", spot)["balances"] if balance["coin"] == MARGIN_COIN), None)
    total = Decimal(0) if usdc is None else decimal_of(usdc["total"])
    held = Decimal(0) if usdc is None else decimal_of(usdc["hold"])
    isolated = sum((position.margin for position in perps.positions if position.isolated), Decimal(0))
    open_result = sum((position.unrealized_pnl for position in perps.positions), Decimal(0))
    return replace(perps, account_value=total + open_result, withdrawable=max(total - held - isolated, Decimal(0)))


def decimal_of(value: object) -> Decimal:
    return Decimal(str(value))


def _position_of(position: _PositionEntry) -> _UserPosition:
    liquidation = position.get("liquidationPx")
    return _UserPosition(
        coin=str(position["coin"]),
        signed_size=decimal_of(position["szi"]),
        leverage=int(position["leverage"]["value"]),
        entry_price=decimal_of(position["entryPx"]),
        mark_price=_mark_price_of(position),
        unrealized_pnl=decimal_of(position["unrealizedPnl"]),
        margin=decimal_of(position["marginUsed"]),
        liquidation_price=None if liquidation is None else decimal_of(liquidation),
        isolated=position["leverage"].get("type") == ISOLATED,
    )


def _mark_price_of(position: _PositionEntry) -> Decimal:
    # The value of the position is at the mark price of the exchange; an open position never has size zero, so a zero
    # here is an answer of unexpected shape and the division fails as one.
    return decimal_of(position["positionValue"]) / abs(decimal_of(position["szi"]))
