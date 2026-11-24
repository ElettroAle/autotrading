from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import UnknownSimulatedProtectionError
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.simulation.simulated_fill import SimulatedFill
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition

DEFAULT_LEVERAGE = 1


@dataclass(frozen=True, slots=True)
class SimulatedProtection:
    """A stop loss or take profit waiting on the simulated exchange, with the identifier the exchange gave it."""

    order_id: str
    order: ProtectionOrder

    @property
    def active(self) -> ActiveProtection:
        return ActiveProtection(self.order_id, self.order.kind, self.order.trigger_price)


@dataclass(frozen=True, slots=True)
class SettledFill:
    """A fill the settlement made on the real prices: of a protection, with its client order id, or a liquidation."""

    fill: SimulatedFill
    client_order_id: ClientOrderId | None


@dataclass(frozen=True, slots=True)
class Settlement:
    book: SimulatedBook
    fills: tuple[SettledFill, ...]


@dataclass(frozen=True, slots=True)
class Reset:
    """The book after a reset, the fills that closed its positions and the movement that brought the balance."""

    book: SimulatedBook
    fills: tuple[SimulatedFill, ...]
    movement: Decimal


@dataclass(frozen=True, slots=True)
class SimulatedBook:
    """Everything the simulated exchange keeps of one account: the virtual account, the leverage set on each asset and
    the protections waiting for their price (R6.3.2).
    """

    account: SimulatedAccount
    leverages: Mapping[str, int] = field(default_factory=dict)
    protections: tuple[SimulatedProtection, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "leverages", MappingProxyType(dict(self.leverages)))

    def with_leverage(self, coin: str, leverage: int) -> SimulatedBook:
        return replace(self, leverages={**self.leverages, coin: leverage})

    def leverage_of(self, coin: str) -> int:
        """The leverage set on the asset, else the one of its open position, else one."""
        held = self.account.position_of(coin)
        return self.leverages.get(coin, DEFAULT_LEVERAGE if held is None else held.leverage)

    def executed(
        self, engine: SimulatedExecution, market: Market, order: MarketOrder, at: datetime
    ) -> tuple[SimulatedBook, SimulatedFill]:
        trade = engine.market_order(self.account, market, order, self.leverage_of(order.coin), at)
        return replace(self, account=_marked(trade.account, market)), trade.fill

    def with_protection(self, protection: SimulatedProtection) -> SimulatedBook:
        return replace(self, protections=(*self.protections, protection))

    def without_protection(self, order_id: str) -> SimulatedBook:
        """Raises UnknownSimulatedProtectionError when it is not waiting: executed or cancelled already."""
        kept = tuple(protection for protection in self.protections if protection.order_id != order_id)
        if len(kept) == len(self.protections):
            raise UnknownSimulatedProtectionError(order_id)
        return replace(self, protections=kept)

    def active(self, coin: str) -> tuple[ActiveProtection, ...]:
        return tuple(protection.active for protection in self.protections if protection.order.asset == coin)

    def settled(self, engine: SimulatedExecution, markets: Mapping[str, Market], at: datetime) -> Settlement:
        """Each position on a market given: liquidated when the price reached its liquidation, else closed by the first
        protection the price reached, else marked at the price. A closed position leaves no protection waiting.
        """
        book: SimulatedBook = self
        fills: tuple[SettledFill, ...] = ()
        for position in self.account.positions:
            market = markets.get(position.coin)
            if market is not None:
                book, settled = book._settled_position(engine, position, market, at)
                fills = (*fills, *settled)
        return Settlement(book, fills)

    def reset(self, balance: Decimal, at: datetime) -> Reset:
        """Every position closed at its last price without fee, every protection and leverage gone, then the balance
        brought to the one given by a movement, so the history explains it (R6.3.2).
        """
        fills = tuple(_closed_at_mark(position, at) for position in self.account.positions)
        realized = sum((fill.realized_pnl for fill in fills), Decimal(0))
        movement = balance - (self.account.balance + realized)
        return Reset(SimulatedBook(SimulatedAccount(balance)), fills, movement)

    def _settled_position(
        self, engine: SimulatedExecution, position: SimulatedPosition, market: Market, at: datetime
    ) -> tuple[SimulatedBook, tuple[SettledFill, ...]]:
        if position.liquidated_at(market.mid_price):
            trade = engine.liquidation(self.account, position, at)
            return self._closed(trade.account, position.coin), (SettledFill(trade.fill, None),)
        hit = next(
            (
                protection
                for protection in self.protections
                if protection.order.asset == position.coin and engine.triggered(protection.order, market.mid_price)
            ),
            None,
        )
        if hit is None:
            return replace(self, account=_marked(self.account, market)), ()
        trade = engine.protection(self.account, market, hit.order, at)
        return self._closed(trade.account, position.coin), (SettledFill(trade.fill, hit.order.client_order_id),)

    def _closed(self, account: SimulatedAccount, coin: str) -> SimulatedBook:
        kept = tuple(protection for protection in self.protections if protection.order.asset != coin)
        return replace(self, account=account, protections=kept)


def _closed_at_mark(position: SimulatedPosition, at: datetime) -> SimulatedFill:
    return SimulatedFill(
        coin=position.coin,
        is_buy=position.direction is Direction.SHORT,
        size=position.size,
        price=position.mark,
        fee=Decimal(0),
        realized_pnl=position.unrealized_pnl(position.mark),
        start_position=position.signed_size,
        liquidation=False,
        executed_at=at,
    )


def _marked(account: SimulatedAccount, market: Market) -> SimulatedAccount:
    held = account.position_of(market.coin)
    if held is None:
        return account
    return account.with_position(market.coin, replace(held, mark_price=market.mid_price))
