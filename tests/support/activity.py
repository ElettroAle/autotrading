"""Readings of an account on the exchange as the tests of the attribution build them (R1.6.1, R1.6.2)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity, AccountFill, AccountPosition, BalanceMovement
from autotrading.domain.flows.trade_intent import TradeSide

CURRENCY = "USDC"
READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def a_position(
    asset: str, *, margin: Decimal = Decimal(0), unrealized_pnl: Decimal = Decimal(0), size: Decimal = Decimal(1)
) -> AccountPosition:
    return AccountPosition(asset, TradeSide.LONG, size, margin, unrealized_pnl)


def a_fill(
    asset: str,
    order_id: UUID | None,
    *,
    realized_pnl: Decimal = Decimal(0),
    fee: Decimal = Decimal(0),
    executed_at: datetime = READ_AT,
    fill_id: str = "1",
) -> AccountFill:
    return AccountFill(fill_id, order_id, asset, Decimal(1), Decimal(100), fee, realized_pnl, executed_at)


def a_movement(amount: Decimal, *, moved_at: datetime = READ_AT, movement_id: str = "0xabc") -> BalanceMovement:
    return BalanceMovement(movement_id, amount, moved_at)


def an_activity(
    *,
    balance: Decimal = Decimal(1000),
    available_margin: Decimal = Decimal(1000),
    positions: tuple[AccountPosition, ...] = (),
    fills: tuple[AccountFill, ...] = (),
    movements: tuple[BalanceMovement, ...] = (),
    read_at: datetime = READ_AT,
) -> AccountActivity:
    return AccountActivity(CURRENCY, balance, available_margin, positions, fills, movements, read_at)
