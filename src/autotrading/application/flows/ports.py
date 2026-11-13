from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import AccountReading, OutsideClosing
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.cycle_record import AbsentSource, CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_cost import CycleCost
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
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.flows.stop_outcome import PositionClosing, PositionOpening
from autotrading.domain.flows.unattributable import UnattributableItem
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

if TYPE_CHECKING:
    from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand


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


@dataclass(frozen=True, slots=True)
class FlowBalance:
    amount: Decimal
    currency: str


class FlowAccountDirectoryPort(Protocol):
    """Bound to the tenant of the request: the accounts it has, as a flow sees them."""

    def exchange_of(self, account_id: UUID) -> str:
        """The exchange the account trades on. Raises FlowAccountNotFoundError for an account the tenant lacks."""
        ...


class FlowAccountBalancePort(Protocol):
    """Bound to the tenant of the request: the balance of an account, read now on its exchange (R0.2.2)."""

    def balance_of(self, account_id: UUID) -> FlowBalance:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the balance cannot be read."""
        ...


@dataclass(frozen=True, slots=True)
class FlowAccountPorts:
    """Where a flow learns of its account: the accounts of the tenant, then the balance read now (ADR 0087)."""

    directory: FlowAccountDirectoryPort
    balances: FlowAccountBalancePort


class FlowAccountPositionsPort(Protocol):
    """Bound to the tenant of the request: the positions open now on an account, before it is removed (R0.2.5)."""

    def open_positions_of(self, account_id: UUID) -> tuple[str, ...]:
        """The assets of the open positions.

        Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the positions cannot be read.
        """
        ...


class FlowAccountRemovalPort(Protocol):
    """Bound to the tenant of the request: the removal of an account, as the accounts context defines it."""

    def has_account(self, account_id: UUID) -> bool:
        """Whether the tenant has the account and has not removed it."""
        ...

    def remove_account(self, account_id: UUID) -> None:
        """Deletes the credentials and hides the account, keeping its history (ADR 0025).

        Raises AccountToRemoveNotFoundError when the tenant has no such account, also when it was already removed.
        """
        ...


@dataclass(frozen=True, slots=True)
class AccountRemovalPorts:
    """What the removal of an account needs of the account itself (ADR 0090)."""

    positions: FlowAccountPositionsPort
    removal: FlowAccountRemovalPort


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
    """Bound to the tenant of the request: it is SelectModelUseCase (R1.4.1, R1.4.2)."""

    def execute(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        """The model with its parameters resolved. Raises InvalidFlowSettingError with the reason."""
        ...


class SourceSettingsPort(Protocol):
    """It is SelectSourceUseCase (R1.3.1)."""

    def execute(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        """The source with its parameters resolved. Raises InvalidFlowSettingError with the reason."""
        ...


class FlowProviderKeysPort(Protocol):
    """Bound to the tenant of the request: the providers it registered a key for (R1.4.1)."""

    def has_key(self, provider: ProviderName) -> bool: ...


class RunningVerificationsPort(Protocol):
    """The procedures of verification in progress on the assets of an account, shared by the API and the worker."""

    def kept_free(self, account_id: UUID, assets: Iterable[str]) -> AbstractContextManager[None]:
        """Keeps the assets of the account free of procedures until the context ends, so none starts while the
        status of a flow on them changes (ADR 0079). Raises AssetUnderVerificationError when one is in progress."""
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
    """Bound to the tenant of the request: what the exchange shows of one of its accounts now (R1.6.1).

    In the worker it is ReadAccountActivityUseCase; in the API, the client that asks the worker for it.
    """

    def execute(self, account_id: UUID) -> AccountActivity:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class SealedAddressPort(Protocol):
    """Bound to the tenant of the request: the account as the worker opens it to read it on its exchange."""

    def sealed_address(self, account_id: UUID) -> SealedAddress:
        """Raises FlowAccountNotFoundError for an account missing or of another tenant (R0.1.3)."""
        ...


class AddressOpenerPort(Protocol):
    """In the worker: opens the sealed credentials of an account only to learn its address (ADR 0007)."""

    def open_address(self, sealed: SealedAddress) -> str:
        """Raises FlowCredentialsNotOpenedError when the sealed text is of another account or no key opens it."""
        ...


class ActivityReaderPort(Protocol):
    """What an exchange shows of an address: positions, balance and movements (R1.6.1)."""

    def activity(self, address: str) -> AccountActivity:
        """Raises FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class FlowPausedNoticePort(Protocol):
    def execute(self, flow_name: str, reason: str) -> None:
        """Tells the user the flow paused on its own, with the reason (R1.2.4, R1.8.2)."""
        ...


class CycleFailedNoticePort(Protocol):
    def execute(self, flow_name: str, reason: str) -> None:
        """Tells the user a cycle of the flow failed, with the message of its error (R1.8.2)."""
        ...


class UnattributableNoticePort(Protocol):
    """In the worker: NotifyUnattributableUseCase (R1.6.2)."""

    def execute(self, items: Sequence[UnattributableItem]) -> None:
        """Tells the user what the account shows that no flow explains, each case the first time found (R1.6.2)."""
        ...


class FlowAccountNamePort(Protocol):
    """Bound to the tenant of the request: the name the user gave an account, to tell it in a notification."""

    def account_name(self, account_id: UUID) -> str:
        """Raises FlowAccountNotFoundError for an account that does not exist or belongs to another tenant."""
        ...


class UnattributablePositionNoticePort(Protocol):
    def execute(self, account_name: str, asset: str) -> None:
        """Tells the user the account holds a position no flow opened (R1.6.2)."""
        ...


class UnattributableFillNoticePort(Protocol):
    def execute(self, account_name: str, asset: str) -> None:
        """Tells the user the account shows an execution no flow ordered (R1.6.2)."""
        ...


class UnattributableMovementNoticePort(Protocol):
    def execute(self, account_name: str, amount: Decimal) -> None:
        """Tells the user the balance of the account changed with no flow behind it (R1.6.2)."""
        ...


class AccountExecutionsPort(Protocol):
    """In the worker: the executions and the funding the exchange still holds of an account since a moment (ADR 0063).

    It is ReadAccountExecutionsUseCase; the window says when part of what was asked is gone already.
    """

    def execute(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class ExecutionsReaderPort(Protocol):
    """The executions and the funding an exchange still holds of an address since a moment (ADR 0063)."""

    def since(self, address: str, since: datetime | None) -> ExecutionsWindow:
        """Raises FlowExchangeUnavailableError when the exchange cannot be read."""
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


class OutsideClosingRecorderPort(Protocol):
    """Bound to the tenant of the request: the history of the closed positions of its flows (R1.7.2)."""

    def execute(self, closing: OutsideClosing) -> None:
        """Records a position the reconciliation finds closed outside the platform (ADR 0056)."""
        ...


class ClosedPositionRepositoryPort(Protocol):
    """Bound to the tenant of the request."""

    def add(self, position: ClosedPosition) -> None:
        """Raises CrossTenantAccessError for a position of another tenant."""
        ...

    def of_flow(self, flow_id: FlowId) -> list[ClosedPosition]: ...


class PositionClosedNoticePort(Protocol):
    def execute(self, flow_name: str, asset: str, pnl: Decimal) -> None:
        """Tells a closing of the flow once, with the PnL its history keeps or the exchange reported (ADR 0070)."""
        ...


class ExecutedFillPort(Protocol):
    """What the exchange executed for an order of a cycle that closed a position, as the orders context reports it."""

    @property
    def average_price(self) -> Decimal: ...

    @property
    def executed_at(self) -> datetime: ...

    @property
    def fee(self) -> Decimal: ...

    @property
    def realized_pnl(self) -> Decimal: ...


class ReportedFillPort(Protocol):
    """What the exchange reported of a closing a user asked: every value missing while it is not confirmed."""

    @property
    def average_price(self) -> Decimal | None: ...

    @property
    def executed_at(self) -> datetime | None: ...

    @property
    def fee(self) -> Decimal | None: ...

    @property
    def realized_pnl(self) -> Decimal | None: ...


@dataclass(frozen=True, slots=True)
class ScheduledFlow:
    """An active flow with the schedule that starts at its last start or resume (R1.2.1)."""

    flow_id: UUID
    schedule: CycleSchedule


@dataclass(frozen=True, slots=True)
class TenantScheduledFlow:
    """An active flow with the tenant it belongs to: the worker runs its cycle on adapters bound to that tenant."""

    tenant_id: TenantId
    flow: ScheduledFlow


@dataclass(frozen=True, slots=True)
class FlowSnapshot[S = object]:
    """The state of the flow read at the start of the cycle; the cycle only needs the names of its active sources.

    The state itself belongs to the flow and travels to the context and the risk check as it is (ADR 0041): its type
    is the one the composition root binds, never known to the cycles context (ADR 0082).
    """

    sources: tuple[str, ...]
    state: S


@dataclass(frozen=True, slots=True)
class SourceRequest[S = object]:
    """The cycle that asks its sources: the flow, its planned instant and the state read at its start.

    Every source reads the configuration of the snapshot, so a change made during the cycle waits for the next one
    (R1.1.3).
    """

    flow_id: UUID
    planned_at: datetime
    snapshot: FlowSnapshot[S]


@dataclass(frozen=True, slots=True)
class SourceReading[D = object]:
    source: str
    data: D


@dataclass(frozen=True, slots=True)
class RiskReview[O = object]:
    """The orders the risk check approved, and the outcome of every decision; the execution orders them (R1.5.5).

    The outcomes travel only to the record: approved, reduced, blocked or discarded (R1.7.1).
    """

    orders: tuple[O, ...]
    outcomes: object


class PlannedFlowsPort(Protocol):
    """The tenants of the flows the worker planned: the actual prices of their forecasts follow (R1.3.5)."""

    def remember(self, entries: Iterable[TenantScheduledFlow]) -> None: ...

    def tenants(self) -> set[TenantId]: ...


@dataclass(frozen=True, slots=True)
class CallAnswered[R]:
    value: R


@dataclass(frozen=True, slots=True)
class CallFailed:
    error: AutotradingError


@dataclass(frozen=True, slots=True)
class CallUnanswered:
    """The call was still running when the wait ended."""


type CallOutcome[R] = CallAnswered[R] | CallFailed | CallUnanswered


class ConcurrentCallsPort(Protocol):
    def call_all[R](self, calls: Mapping[str, Callable[[], R]], seconds: float) -> dict[str, CallOutcome[R]]:
        """Runs every call at once and waits for them only up to the seconds; a call still running is abandoned.

        A call that fails with an error of the project ends with it; any other error is raised.
        """
        ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class TenantScheduledFlowsPort(Protocol):
    def active_of_every_tenant(self) -> list[TenantScheduledFlow]:
        """Every active flow of every tenant, with the tenant it belongs to."""
        ...


class CycleRepositoryPort(Protocol):
    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        """Takes the planned instant of the flow for this executor; False when another one already took it."""
        ...

    def record(self, record: CycleRecord) -> None: ...


class FlowLockPort(Protocol):
    def hold(self, flow_id: UUID) -> AbstractContextManager[bool]:
        """Holds the flow for one cycle, across processes; yields False at once when a cycle is still running."""
        ...


class CycleLauncherPort(Protocol):
    def launch(self, task: Callable[[], object]) -> None:
        """Runs the cycle apart from the others, so a slow flow never delays another (R1.2.1)."""
        ...


class FlowStatePort[S = object, E = object](Protocol):
    def read(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot[S]:
        """The state of the flow at the start of the cycle; the anchor is the start of its schedule."""
        ...

    def update(self, flow_id: UUID, anchor: datetime, executions: Sequence[E]) -> object:
        """Applies the executions of the cycle and gives back the state of the flow at the end of it."""
        ...


class SourcePort[S = object, D = object](Protocol):
    def collect(self, request: SourceRequest[S], source: str) -> D:
        """The data of one active source; any typed error makes the source absent for the cycle (R1.2.5)."""
        ...


class ContextPort[S = object, D = object, C = object](Protocol):
    def compose(
        self,
        flow_id: UUID,
        snapshot: FlowSnapshot[S],
        readings: Sequence[SourceReading[D]],
        absent: Sequence[AbsentSource],
    ) -> C:
        """The context of the agent, declaring the missing data."""
        ...


class AgentPort[C = object, A = object](Protocol):
    def decide(self, flow_id: UUID, context: C) -> A: ...


class RiskPort[S = object, A = object, O = object](Protocol):
    def check(self, flow_id: UUID, snapshot: FlowSnapshot[S], decisions: A) -> RiskReview[O]: ...


class OrderPort[O = object, E = object](Protocol):
    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[O]) -> Sequence[E]:
        """Sends the approved orders of the cycle, closings first, and gives back their real outcomes (R1.5.5)."""
        ...


class FlowPausePort(Protocol):
    def execute(self, command: PauseAffectedFlowsCommand) -> object:
        """Pauses every active flow the permanent error involves, with the message of the error as reason (R1.2.4)."""
        ...


class CycleFailureNoticePort(Protocol):
    def execute(self, flow_id: UUID, reason: str) -> None:
        """Tells the user the cycle of the flow failed, with the message of its error (R1.8.2)."""
        ...


class CycleJournalPort(Protocol):
    """Describes for the record what the steps produced: only the contexts behind the steps know their data."""

    def describe(self, step: CycleStep, result: object) -> Mapping[str, object]:
        """The result of the step as JSON data; a credential never appears in it (R1.7.1)."""
        ...

    def call_cost(self, decision: object) -> CallCost | None:
        """Tokens and cost of the model call behind the decision of the agent (R1.4.6)."""
        ...


class CycleHistoryPort(Protocol):
    """Bound to the tenant of the request: it never shows the cycles of a flow of another tenant."""

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        """The cycles of the flow from the most recent planned instant."""
        ...

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None: ...

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        """The cost of every cycle of the flow that called the model."""
        ...


@dataclass(frozen=True, slots=True)
class FlowSummary:
    """A flow in use as the consultation shows it; the schedule is None unless the flow is active (R1.7.3)."""

    flow_id: UUID
    name: str
    account: str
    status: str
    pause_reason: str | None
    model: str
    schedule: CycleSchedule | None


class FlowSummaryPort(Protocol):
    """Bound to the tenant of the request: its flows in use, never another tenant's."""

    def in_use(self) -> list[FlowSummary]: ...


class FlowDirectoryPort(Protocol):
    def exists(self, flow_id: UUID) -> bool:
        """True when the flow belongs to the tenant of the request."""
        ...
