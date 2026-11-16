from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.user_id import UserId


class OrderAccountPort(Protocol):
    """Bound to the tenant of the request: the accounts the orders are sent for."""

    def sealed_access(self, account_id: UUID) -> SealedAccess:
        """Raises OrderAccountNotFoundError for an account that does not exist or belongs to another tenant."""
        ...


class AccessOpenerPort(Protocol):
    """Opens sealed credentials with the private key only the worker holds (ADR 0007)."""

    def open_access(self, sealed: SealedAccess) -> TradingAccess:
        """Raises OrderCredentialsNotOpenedError when the sealed text names another tenant or account, or no key opens
        it.
        """
        ...


class ExchangePort(Protocol):
    """Orders on the exchange. Raises OrderExchangeUnavailableError when the exchange cannot be reached."""

    def market(self, access: TradingAccess, coin: str) -> Market: ...

    def position(self, access: TradingAccess, coin: str) -> HeldPosition | None:
        """The position open on the asset, or None when there is none."""

    def set_leverage(self, access: TradingAccess, coin: str, leverage: int, margin: MarginMode) -> None:
        """Sets the leverage of the asset with the given margin mode.

        Raises ExchangeRejectedOrderError when the exchange refuses the leverage or the margin mode.
        """

    def place_market_order(self, access: TradingAccess, order: MarketOrder) -> Execution:
        """What the exchange executed, read from its fills.

        Raises ExchangeRejectedOrderError with the message of the exchange when nothing is executed, and
        OrderNotAcknowledgedError when the exchange does not confirm the order in time. Never retries.
        """

    def find_order(self, access: TradingAccess, order: MarketOrder) -> Execution | None:
        """The execution of an order looked up by its client order id, or None if the exchange has none."""


class ProtectionExchangePort(Protocol):
    """Stop loss and take profit on the exchange, over the whole position of an asset (R3.1.2).

    Raises OrderExchangeUnavailableError when the exchange cannot be reached.
    """

    def place(self, access: TradingAccess, order: ProtectionOrder) -> str:
        """The identifier the exchange gave the protection, waiting for its price.

        Raises ExchangeRejectedOrderError with the message of the exchange when it refuses it.
        """
        ...

    def cancel(self, access: TradingAccess, asset: str, order_id: str) -> None:
        """Raises ExchangeRejectedOrderError when the exchange no longer has it: executed or cancelled already."""
        ...

    def active(self, access: TradingAccess, asset: str) -> tuple[ActiveProtection, ...]:
        """The protections waiting on the exchange for the position on the asset."""
        ...


class ProtectionRepositoryPort(Protocol):
    """The protections the platform placed for the flows of the tenant, bound to it like every port of owned data."""

    def add(self, protection: PlacedProtection) -> None: ...

    def placed(self, account_id: UUID, asset: str) -> tuple[PlacedProtection, ...]:
        """The protections recorded for the position of the account on the asset: one flow at most has it (R1.1.2)."""
        ...

    def remove(self, account_id: UUID, asset: str) -> None: ...


class ProtectedPositionPort(Protocol):
    """The position of an account on an asset whose protections are left behind by its closing (R3.1.2)."""

    @property
    def account_id(self) -> UUID: ...

    @property
    def asset(self) -> str: ...


class VerificationAssetPort(Protocol):
    """An asset of an account, as the procedure of verification asks about it (R0.4.1)."""

    @property
    def account_id(self) -> UUID: ...

    @property
    def coin(self) -> str: ...


class VerificationClosingPort(VerificationAssetPort, Protocol):
    """The position the procedure of verification closes, with the user who launched it (R0.4.1, ADR 0024)."""

    @property
    def user_id(self) -> UserId: ...


class VerificationOpeningPort(VerificationClosingPort, Protocol):
    """The position the procedure of verification opens, with the user who launched it (R0.4.1, ADR 0024)."""

    @property
    def side(self) -> str: ...

    @property
    def leverage(self) -> int: ...

    @property
    def value(self) -> Decimal: ...


class FlowPositionToClosePort(Protocol):
    """A position a flow asks to close: the whole position of its account on one asset (R1.1.5)."""

    @property
    def account_id(self) -> UUID: ...

    @property
    def asset(self) -> str: ...

    @property
    def user_id(self) -> UserId: ...


class PositionClosingPort(Protocol):
    """Asks the worker, the only service holding the private key, to close a position of the tenant (ADR 0023).

    Raises OrderAccountNotFoundError, NoOpenPositionError, OrderExchangeUnavailableError, and
    OrderWorkerUnavailableError when the worker cannot be reached or answers in an unexpected shape.
    """

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome: ...


class OrderRepositoryPort(Protocol):
    """The orders of the tenant, bound to it like every port of owned data."""

    def add(self, order: Order) -> None: ...


class OrderRejectedNoticePort(Protocol):
    def execute(self, flow_name: str, message: str) -> None:
        """Tells the user the exchange refused an order of the flow, with its message (R1.8.2)."""
        ...


class PositionOpenedNoticePort(Protocol):
    def execute(self, flow_name: str, asset: str, direction: str, leverage: int, value: Decimal) -> None:
        """Tells the user the flow opened a position, with the value the exchange executed (R1.8.2)."""
        ...


class FlowClosingRecorderPort(Protocol):
    def execute(self, flow_id: UUID, cycle: datetime, asset: str, fill: Execution, *, unprotected: bool) -> None:
        """Records in the history of the flow a position an order of its cycle closed (R1.7.2): unprotected when it
        closed because the exchange refused its stop loss (R3.1.2).
        """
        ...


class ManualClosingRecorderPort(Protocol):
    def execute(self, account_id: UUID, asset: str, fill: OrderOutcome) -> None:
        """Records in the history of the flow that trades the asset a position a user closed by hand (ADR 0061)."""
        ...


class ApprovedOrderPort(Protocol):
    """An order a cycle of a flow got through the risk check, as the flows context hands it over."""

    def order_with[T](
        self,
        opening: Callable[[str, str, Decimal, int, Decimal | None, Decimal | None], T],
        closing: Callable[[str], T],
    ) -> T:
        """Builds the order with the opening (asset, side, value, leverage, stop and target of the exit plan) or the
        closing (asset) it needs.
        """
        ...


class CycleOrdersPort(Protocol):
    """The approved orders of one cycle of a flow, for the account of the flow."""

    @property
    def account_id(self) -> UUID: ...

    @property
    def flow_id(self) -> UUID: ...

    @property
    def flow_name(self) -> str: ...

    @property
    def planned_at(self) -> datetime: ...

    @property
    def orders(self) -> Sequence[ApprovedOrderPort]: ...

    @property
    def assets(self) -> Sequence[str]:
        """The assets of the flow: a position on one of them without a stop loss gets the default one (R3.1.2)."""
        ...

    @property
    def default_stop_loss_percent(self) -> Decimal: ...

    @property
    def default_take_profit_percent(self) -> Decimal | None: ...
