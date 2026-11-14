"""Readings of an account on the exchange as the tests of the attribution build them (R1.6.1, R1.6.2)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition, BalanceMovement
from autotrading.domain.flows.ledger import Execution, FundingPayment
from autotrading.domain.flows.trade_intent import TradeSide

CURRENCY = "USDC"
READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def a_position(
    asset: str,
    *,
    margin: Decimal = Decimal(0),
    unrealized_pnl: Decimal = Decimal(0),
    size: Decimal = Decimal(1),
    leverage: int = 1,
    entry_price: Decimal = Decimal(100),
) -> AccountPosition:
    return AccountPosition(asset, TradeSide.LONG, size, margin, unrealized_pnl, leverage, entry_price)


def a_fill(
    asset: str,
    order_id: UUID | None,
    *,
    realized_pnl: Decimal = Decimal(0),
    fee: Decimal = Decimal(0),
    executed_at: datetime = READ_AT,
    fill_id: str = "1",
    size: Decimal = Decimal(1),
    start_position: Decimal = Decimal(0),
    liquidation: bool = False,
) -> Execution:
    """An execution of the account; its exchange order is its fill, so two fills are two executions."""
    return Execution(
        fill_id=fill_id,
        exchange_order_id=f"o-{fill_id}",
        order_id=order_id,
        asset=asset,
        size=size,
        price=Decimal(100),
        fee=fee,
        realized_pnl=realized_pnl,
        start_position=start_position,
        liquidation=liquidation,
        executed_at=executed_at,
    )


def a_payment(asset: str, amount: Decimal, *, paid_at: datetime = READ_AT) -> FundingPayment:
    return FundingPayment(asset, amount, paid_at)


def a_movement(amount: Decimal, *, moved_at: datetime = READ_AT, movement_id: str = "0xabc") -> BalanceMovement:
    return BalanceMovement(movement_id, amount, moved_at)


def an_activity(
    *,
    balance: Decimal = Decimal(1000),
    available_margin: Decimal = Decimal(1000),
    positions: tuple[AccountPosition, ...] = (),
    movements: tuple[BalanceMovement, ...] = (),
    read_at: datetime = READ_AT,
) -> AccountActivity:
    return AccountActivity(CURRENCY, balance, available_margin, positions, movements, read_at)
