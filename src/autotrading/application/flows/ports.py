from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import AccountReading, OutsideClosing
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_timing import FlowTiming
from autotrading.domain.flows.ledger import (
    AccountLedger,
    ExecutionsWindow,
    FlowTotals,
    LedgerEntry,
    LedgerKeys,
    PlatformOrders,
)
from autotrading.domain.flows.operations import Operation, OperationsOwner, OperationsQuery, OperationsReport
from autotrading.domain.flows.risk_check import AssetLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.flows.stop_outcome import PositionClosing, PositionOpening
from autotrading.domain.flows.unattributable import UnattributableItem
from autotrading.domain.tenancy.user_id import UserId


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

    def close(self, account_id: UUID, asset: str, user_id: UserId) -> PositionClosing | None:
        """Closes the whole position on the asset, through the worker that holds the key (ADR 0023).

        None when there was no position; otherwise the fill, or the reason the exchange or the worker gave.
        """
        ...


class FlowOpeningsPort(Protocol):
    """Bound to the tenant of the request: the openings the flows sent, from the orders the platform recorded."""

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        """The last executed order of the flow that opened a position on the asset, or None if it never did."""
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


class AutomaticPausePort(Protocol):
    """Bound to the tenant of the flows it pauses."""

    def pause(self, flow_ids: Sequence[FlowId], reason: str) -> None:
        """Pauses the flows still active, with the reason of the automatic pause; the others stay as they are."""
        ...


class FlowTimingPort(Protocol):
    """Bound to the tenant of the request: the instant every flow last started or resumed, and its pause reason."""

    def timings(self) -> Mapping[FlowId, FlowTiming]: ...


class AccountActivityPort(Protocol):
    """Bound to the tenant of the request: what the exchange shows of one of its accounts now (R1.6.1)."""

    def activity(self, account_id: UUID) -> AccountActivity:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class PausedFlowNoticePort(Protocol):
    def paused(self, flow: Flow, reason: str) -> None:
        """Tells the user the flow paused on its own, with the reason (R1.2.4, R1.8.2)."""
        ...


class UnattributableNoticePort(Protocol):
    def notice(self, items: Sequence[UnattributableItem]) -> None:
        """Tells the user what the account shows that no flow explains, each case the first time found (R1.6.2)."""
        ...


class AccountExecutionsPort(Protocol):
    """In the worker: the executions and the funding the exchange still holds of an account since a moment (ADR 0063).

    Without a moment, everything the exchange still holds; the window says when part of it is gone already.
    """

    def since(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class FlowLedgerPort(Protocol):
    """Bound to the tenant of the request: the ledger of the executions of its accounts and the running totals of
    every flow, kept together (ADR 0063).
    """

    def cursor(self, account_id: UUID) -> datetime | None:
        """The moment of the most recent execution or funding recorded for the account, or None before the first."""
        ...

    def recorded_since(self, account_id: UUID, since: datetime) -> LedgerKeys:
        """What of the account is recorded already from that moment on, to read the overlap of two windows once."""
        ...

    def record(self, account_id: UUID, ledger: AccountLedger, cursor: datetime) -> tuple[LedgerEntry, ...]:
        """Records what is new and adds it to the totals of its flows in the same transaction; returns what was new."""
        ...

    def totals_of(self, flow_ids: Iterable[FlowId]) -> Mapping[FlowId, FlowTotals]:
        """The running totals of those flows; a flow without any execution yet has none."""
        ...


class FlowOperationsPort(Protocol):
    """Bound to the tenant of the request: the ledger as its owner reads it (ADR 0074, ADR 0080).

    For an account the tenant does not have, both methods raise FlowAccountNotFoundError; the export raises it before
    returning, never while its rows are read.
    """

    def report(self, owner: OperationsOwner, query: OperationsQuery) -> OperationsReport:
        """The page of the query, newest first, and the totals of every row the query admits, whatever the page."""
        ...

    def export(self, owner: OperationsOwner, query: OperationsQuery) -> Iterator[Operation]:
        """Every row the query admits, whatever the page, oldest first, read as it is consumed."""
        ...


class PlatformOrdersPort(Protocol):
    """Bound to the tenant of the request: the orders the platform sent, from the orders context."""

    def orders_among(self, account_id: UUID, order_ids: Iterable[UUID]) -> PlatformOrders:
        """Those of the client order ids the platform sent on the account, with the flow that sent it, or None."""
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
