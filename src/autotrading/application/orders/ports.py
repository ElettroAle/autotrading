from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.application.orders.outcome import OrderOutcome
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.user_id import UserId


class TradingAccessPort(Protocol):
    """Opens, for an account of the tenant, what signs its orders.

    Raises OrderAccountNotFoundError for an account that does not exist or belongs to another tenant.
    """

    def access(self, account_id: UUID) -> TradingAccess: ...


class ExchangePort(Protocol):
    """Orders on the exchange. Raises OrderExchangeUnavailableError when the exchange cannot be reached."""

    def market(self, access: TradingAccess, coin: str) -> Market: ...

    def position(self, access: TradingAccess, coin: str) -> HeldPosition | None:
        """The position open on the asset, or None when there is none."""

    def set_leverage(self, access: TradingAccess, coin: str, leverage: int) -> None:
        """Raises ExchangeRejectedOrderError when the exchange refuses the leverage."""

    def place_market_order(self, access: TradingAccess, order: MarketOrder) -> Execution:
        """What the exchange executed, read from its fills.

        Raises ExchangeRejectedOrderError with the message of the exchange when nothing is executed, and
        OrderNotAcknowledgedError when the exchange does not confirm the order in time. Never retries.
        """

    def find_order(self, access: TradingAccess, order: MarketOrder) -> Execution | None:
        """The execution of an order looked up by its client order id, or None if the exchange has none."""


class PositionClosingPort(Protocol):
    """Asks the worker, the only service holding the private key, to close a position of the tenant (ADR 0023).

    Raises OrderAccountNotFoundError, NoOpenPositionError, OrderExchangeUnavailableError, and
    OrderWorkerUnavailableError when the worker cannot be reached or answers in an unexpected shape.
    """

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome: ...


class OrderRepositoryPort(Protocol):
    """The orders of the tenant, bound to it like every port of owned data."""

    def add(self, order: Order) -> None: ...


class FlowOrderEventsPort(Protocol):
    """What the orders of one cycle of a flow left behind, told to the flow that sent them (R1.7.2, R1.8.2)."""

    def rejected(self, message: str) -> None: ...

    def opened(self, coin: str, direction: str, leverage: int, value: Decimal) -> None: ...

    def closed(self, coin: str, execution: Execution) -> None: ...
