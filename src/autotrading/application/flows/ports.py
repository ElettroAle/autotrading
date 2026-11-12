from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import AccountReading, OutsideClosing, PlatformOrders
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.risk_check import AssetLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.flows.unattributable import UnattributableItem


@dataclass(frozen=True, slots=True)
class FlowAccount:
    """What a flow needs of its account: the exchange it trades on and the balance read from it now."""

    exchange: str
    balance: Decimal
    currency: str


class FlowRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the flows of another tenant."""

    def list(self) -> list[Flow]:
        """Every flow of the tenant with the configuration version in force."""
        ...

    def name_in_use(self, name: FlowName) -> bool:
        """True when a flow of the tenant not archived has the name."""
        ...

    def add(self, flow: Flow) -> None:
        """Saves the flow with its first configuration version.

        Raises FlowNameInUseError, or FlowAccountNotFoundError when the account is not of the tenant any more.
        """
        ...

    def get(self, flow_id: FlowId) -> Flow:
        """The flow with the configuration version in force. Raises FlowNotFoundError."""
        ...

    def version(self, flow_id: FlowId, number: int) -> FlowConfiguration:
        """One configuration version of the flow. Raises FlowNotFoundError or FlowVersionNotFoundError."""
        ...

    def change_status(self, flow: Flow) -> None:
        """Saves the status of the flow. Raises FlowNotFoundError."""
        ...

    def add_version(self, flow: Flow) -> None:
        """Saves the configuration of the flow as a new version, the others untouched. Raises FlowNotFoundError."""
        ...

    def add_capital_change(self, flow: Flow, change: CapitalChange) -> None:
        """Saves, together, the version with the new capital and the change in its history. Raises FlowNotFoundError."""
        ...

    def capital_changes(self, flow_id: FlowId) -> tuple[CapitalChange, ...]:
        """The changes of the capital allocated to the flow, oldest first. Raises FlowNotFoundError."""
        ...


class FlowAccountPort(Protocol):
    """Bound to the tenant of the request."""

    def account(self, account_id: UUID) -> FlowAccount:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the balance cannot be read."""
        ...


class FlowPositionsPort(Protocol):
    """Bound to the tenant of the request: the positions of a flow are those of its account on its assets (R1.1.2)."""

    def close(self, account_id: UUID, asset: str, user_id: UserId) -> str | None:
        """Closes the whole position on the asset, through the worker that holds the key (ADR 0023).

        None when the position is closed or there was none; otherwise the reason the exchange or the worker gave.
        """
        ...

    def committed_margin(self, account_id: UUID, assets: tuple[str, ...]) -> Decimal:
        """The margin the open positions on the assets hold now. Raises FlowExchangeUnavailableError."""
        ...


class RunningCyclePort(Protocol):
    def wait_until_finished(self, flow_id: FlowId) -> None:
        """Returns once no cycle of the flow is running, across processes; at once when none is (R1.1.5)."""
        ...


class MarketsPort(Protocol):
    def tradable_assets(self) -> frozenset[str]:
        """The assets the exchange trades now. Raises FlowExchangeUnavailableError."""
        ...


class ModelSettingsPort(Protocol):
    """Bound to the tenant of the request: a model is usable only with the key of its provider (R1.4.1)."""

    def selection(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        """The model with its parameters resolved. Raises InvalidFlowSettingError with the reason."""
        ...


class SourceSettingsPort(Protocol):
    def selection(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        """The source with its parameters resolved. Raises InvalidFlowSettingError with the reason."""
        ...


class ExchangeLimitsPort(Protocol):
    """What the exchange of the account of the flow accepts on an asset, read now (R1.5.2, R1.5.4)."""

    def limits(self, asset: str) -> AssetLimits | None:
        """None when the exchange does not trade the asset. Raises FlowExchangeUnavailableError."""
        ...


class AccountActivityPort(Protocol):
    """Bound to the tenant of the request: what the exchange shows of one of its accounts now (R1.6.1)."""

    def activity(self, account_id: UUID) -> AccountActivity:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class PlatformOrdersPort(Protocol):
    """Bound to the tenant of the request: the orders the platform sent, from the orders context."""

    def orders_of_account(self, account_id: UUID) -> PlatformOrders:
        """The client order id of every order sent on the account, with the flow that sent it, or None."""
        ...


class ReconciliationRepositoryPort(Protocol):
    """Bound to the tenant of the request: the readings of its accounts and what no flow explains (R1.6.2)."""

    def last_reading(self, account_id: UUID) -> AccountReading | None: ...

    def save_reading(self, reading: AccountReading) -> None:
        """Replaces the last reading of the account."""
        ...

    def record(self, item: UnattributableItem) -> bool:
        """Records the item unless the same case is already recorded; True when it is new."""
        ...

    def resolve_positions(self, account_id: UUID, open_assets: frozenset[str]) -> None:
        """Closes the recorded positions no longer open: a new position on that asset is a new case."""
        ...


class ClosedPositionsPort(Protocol):
    """Bound to the tenant of the request: the history of the closed positions of its flows (R1.7.2)."""

    def add_closed_outside(self, closing: OutsideClosing) -> None: ...


class ClosedPositionRepositoryPort(Protocol):
    """Bound to the tenant of the request."""

    def add(self, position: ClosedPosition) -> None:
        """Raises CrossTenantAccessError for a position of another tenant."""
        ...

    def of_flow(self, flow_id: FlowId) -> list[ClosedPosition]: ...
