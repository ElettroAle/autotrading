from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import (
    InsufficientMarginError,
    OrderBelowMinimumValueError,
    OrderSizeOffStepError,
    ReduceOnlyWithoutPositionError,
)
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_fill import SimulatedFill, SimulatedTrade
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition
from autotrading.domain.orders.slippage import Slippage

ZERO = Decimal(0)
ONE = Decimal(1)
# The margin a position must keep is half the one it holds at the largest leverage of the asset, as on Hyperliquid.
MAINTENANCE_SHARE = Decimal(2)


@dataclass(frozen=True, slots=True)
class _Split:
    """How much of an order closes the position held and how much opens one in its own direction."""

    closed: Decimal
    opened: Decimal


@dataclass(frozen=True, slots=True)
class _Execution:
    market: Market
    order: MarketOrder
    split: _Split
    price: Decimal
    leverage: int

    @property
    def size(self) -> Decimal:
        return self.split.closed + self.split.opened

    @property
    def fee(self) -> Decimal:
        return self.size * self.price * self.market.taker_fee_rate


class SimulatedExecution:
    """Executes orders on a virtual account with the rules of the real market (R6.3.2), the engine the replay reuses
    (R4.2.3).

    An order executes at the current price moved against it by the slippage of the simulation, never beyond the one the
    order accepts, and pays the fee of the market on its value. Positions hold isolated margin (ADR 0095).
    """

    def __init__(self, slippage: Slippage) -> None:
        self._slippage = slippage

    def market_order(
        self, account: SimulatedAccount, market: Market, order: MarketOrder, leverage: int, at: datetime
    ) -> SimulatedTrade:
        """Raises the errors of the rules of the market, InsufficientMarginError and ReduceOnlyWithoutPositionError."""
        market.require_leverage(leverage)
        _require_on_step(market, order)
        held = account.position_of(order.coin)
        split = _split_of(order, held, market)
        price = self._price(market.mid_price, order)
        return _executed(account, held, _Execution(market, order, split, price, leverage), at)

    def protection(
        self, account: SimulatedAccount, market: Market, protection: ProtectionOrder, at: datetime
    ) -> SimulatedTrade:
        """The whole position closed at the market, the price of the protection being reached."""
        held = account.position_of(protection.asset)
        if held is None or held.direction is not protection.closing_direction:
            raise ReduceOnlyWithoutPositionError(protection.asset)
        closing = held.held.closing_order(self._slippage)
        return self.market_order(account, market, closing, held.leverage, at)

    @staticmethod
    def liquidation(account: SimulatedAccount, position: SimulatedPosition, at: datetime) -> SimulatedTrade:
        """The position closed at its liquidation price: it loses at most its margin and pays no fee."""
        price = position.liquidation_price
        realized = max(position.unrealized_pnl(price), -position.margin)
        fill = SimulatedFill(
            coin=position.coin,
            is_buy=position.direction is Direction.SHORT,
            size=position.size,
            price=price,
            fee=ZERO,
            realized_pnl=realized,
            start_position=position.signed_size,
            liquidation=True,
            executed_at=at,
        )
        return SimulatedTrade(fill, account.with_position(position.coin, None).moved(realized))

    @staticmethod
    def triggered(protection: ProtectionOrder, price: Decimal) -> bool:
        """Whether the price reached the protection: a stop loss against the position, a take profit in its favour."""
        protects_long = protection.closing_direction is Direction.LONG
        limits_loss = protection.kind is ProtectionKind.STOP_LOSS
        if protects_long == limits_loss:
            return price <= protection.trigger_price
        return price >= protection.trigger_price

    def _price(self, mid_price: Decimal, order: MarketOrder) -> Decimal:
        slippage = min(self._slippage.fraction, order.slippage.fraction)
        return mid_price * (ONE + slippage) if order.is_buy else mid_price * (ONE - slippage)


def _require_on_step(market: Market, order: MarketOrder) -> None:
    if order.size <= 0 or order.size != order.size.quantize(market.size_step):
        raise OrderSizeOffStepError(order.coin, market.size_step)


def _split_of(order: MarketOrder, held: SimulatedPosition | None, market: Market) -> _Split:
    if order.reduce_only:
        if held is None or held.direction is not order.direction:
            raise ReduceOnlyWithoutPositionError(order.coin)
        return _Split(min(order.size, held.size), ZERO)
    if order.size * market.mid_price < market.min_order_value:
        raise OrderBelowMinimumValueError(order.coin, market.min_order_value)
    if held is None or held.direction is order.direction:
        return _Split(ZERO, order.size)
    closed = min(order.size, held.size)
    return _Split(closed, order.size - closed)


def _executed(
    account: SimulatedAccount, held: SimulatedPosition | None, execution: _Execution, at: datetime
) -> SimulatedTrade:
    coin = execution.order.coin
    realized, remaining = _closing(held, execution)
    position = _opening(remaining, execution)
    after = account.with_position(coin, position).moved(realized - execution.fee)
    if execution.split.opened and after.available_margin < 0:
        raise InsufficientMarginError(coin)
    fill = SimulatedFill(
        coin=coin,
        is_buy=execution.order.is_buy,
        size=execution.size,
        price=execution.price,
        fee=execution.fee,
        realized_pnl=realized,
        start_position=ZERO if held is None else held.signed_size,
        liquidation=False,
        executed_at=at,
    )
    return SimulatedTrade(fill, after)


def _closing(held: SimulatedPosition | None, execution: _Execution) -> tuple[Decimal, SimulatedPosition | None]:
    """The PnL the order realizes on the position held, and what is left of it."""
    closed = execution.split.closed
    if held is None or not closed:
        return ZERO, held
    realized = (execution.price - held.entry_price) * (closed if held.direction is Direction.LONG else -closed)
    if closed == held.size:
        return realized, None
    left = held.size - closed
    return realized, _resized(held, left, held.margin * left / held.size, held.entry_price)


def _opening(held: SimulatedPosition | None, execution: _Execution) -> SimulatedPosition | None:
    """The position after the part of the order that opens, added to the one held on the same side."""
    opened = execution.split.opened
    if not opened:
        return held
    margin = opened * execution.price / execution.leverage
    if held is None:
        maintenance = ONE / (MAINTENANCE_SHARE * execution.market.max_leverage)
        order = execution.order
        return SimulatedPosition(
            order.coin, order.direction, opened, execution.leverage, execution.price, margin, maintenance
        )
    size = held.size + opened
    entry = (held.entry_price * held.size + execution.price * opened) / size
    return _resized(held, size, held.margin + margin, entry)


def _resized(held: SimulatedPosition, size: Decimal, margin: Decimal, entry: Decimal) -> SimulatedPosition:
    return SimulatedPosition(held.coin, held.direction, size, held.leverage, entry, margin, held.maintenance_rate)
