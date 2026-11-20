from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import AccountReading, OutsideClosing, ProtectionClosing
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.capital_history import AccountTransfer
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_filter import CycleFilter
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrders
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import AbsentSource, CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.emergency_closing import EmergencyClosing
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.exit_plan import ExitPlan, PlacedLevels
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_cost import CycleCost
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_key import FlowKey
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_timing import FlowTiming
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    ClosedPositionHistoryTotals,
    CycleHistoryEntry,
    HistoryQuery,
    OrderHistoryEntry,
    OrderHistoryTotals,
)
from autotrading.domain.flows.ledger import (
    AccountLedger,
    ExecutionsWindow,
    FlowTotals,
    LedgerKeys,
    PlatformOrders,
)
from autotrading.domain.flows.loss_guard import LossReferences
from autotrading.domain.flows.openings_suspension import OpeningsStatus, OpeningsSuspension
from autotrading.domain.flows.operations import Operation, OperationsOwner, OperationsQuery, OperationsReport
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.recorded_decision import DatedDecision, DecidedCycle, RecordedDecision
from autotrading.domain.flows.risk_check import AssetLimits
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.flows.selections import ActiveSource, ModelSelection, SourceSelection
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.unattributable import UnattributableItem
from autotrading.domain.flows.unattributable_page import UnattributableCursor, UnattributableFilter, UnattributablePage
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

if TYPE_CHECKING:
    from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
    from autotrading.application.flows.pause_flows_on_expired_keys import PauseFlowsOnExpiredKeysCommand
    from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand
    from autotrading.application.flows.record_account_executions import RecordAccountExecutionsCommand


@dataclass(frozen=True, slots=True)
class FlowVersion:
    """One configuration version of a flow as a list shows it: its number and when it was saved (R2.3.5)."""

    number: int
    created_at: datetime


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

    def versions(self, flow_id: FlowId) -> tuple[FlowVersion, ...]:
        """Every configuration version of the flow, newest first. Raises FlowNotFoundError."""
        ...

    def change_status(self, flow: Flow) -> None:
        """Saves the status of the flow. Raises FlowNotFoundError."""
        ...

    def rename(self, flow: Flow) -> None:
        """Saves the name of the flow, its versions untouched. Raises FlowNotFoundError or FlowNameInUseError."""
        ...

    def add_version(self, flow: Flow) -> None:
        """Saves the configuration of the flow as a new version, the others untouched. Raises FlowNotFoundError."""
        ...

    def add_capital_change(self, flow: Flow, change: CapitalChange) -> None:
        """Saves, together, the version with the new capital, when the capital changes, and the change in its history.

        A cash-out that keeps the capital records the change on the version in force (R3.4.1). Raises
        FlowNotFoundError.
        """
        ...

    def capital_changes_of(self, flow_ids: Iterable[FlowId]) -> Mapping[FlowId, tuple[CapitalChange, ...]]:
        """Every change of the capital of each of those flows, oldest first; a flow never changed has none.

        They carry the profits cashed out (R3.4.1) and chain the return (R3.4.3). A flow of another tenant has none.
        """
        ...

    def add_assignment(self, flow: Flow) -> None:
        """Saves, together, the account of the draft and the version with its capital and assets (ADR 0124, ADR
        bozza-configurata-dall-editor-e-duplica-con-conto).

        Raises FlowNotFoundError, or FlowAccountNotFoundError when the account is not of the tenant any more.
        """
        ...

    def capital_changes(self, flow_ids: Iterable[FlowId], window: TimeWindow, limit: int) -> tuple[CapitalChange, ...]:
        """The most recent changes of the capital of those flows in the window, at most `limit`, newest first (R3.4.2).

        A flow of another tenant has none.
        """
        ...

    def count_capital_changes(self, flow_ids: Iterable[FlowId], window: TimeWindow) -> int:
        """How many changes of the capital of those flows the window holds (R3.4.2)."""
        ...


class FlowAccountDirectoryPort(Protocol):
    """Bound to the tenant of the request: the accounts it has, as a flow sees them."""

    def exchange_of(self, account_id: UUID) -> str:
        """The exchange the account trades on. Raises FlowAccountNotFoundError for an account the tenant lacks."""
        ...


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


@dataclass(frozen=True, slots=True)
class PositionToClose:
    """The position of a flow to close: the whole position of its account on one of its assets (R1.1.2)."""

    account_id: UUID
    asset: str
    user_id: UserId


class ClosingAnswerPort(Protocol):
    """What closing a position gave, as data: found or not, the fill confirmed in time, or the reason it was not."""

    @property
    def found(self) -> bool: ...

    @property
    def refusal(self) -> str | None: ...

    @property
    def average_price(self) -> Decimal | None: ...

    @property
    def executed_at(self) -> datetime | None: ...

    @property
    def fee(self) -> Decimal | None: ...

    @property
    def realized_pnl(self) -> Decimal | None: ...


class FlowPositionsPort(Protocol):
    """It is CloseFlowPositionUseCase of the orders context, bound to the tenant of the request (ADR 0023, ADR 0055).

    The position is closed through the worker, the only service that holds the key; the answer never raises.
    """

    def execute(self, position: PositionToClose) -> ClosingAnswerPort: ...


class FlowOpeningsPort(Protocol):
    """Bound to the tenant of the request: the openings the flows sent, from the orders the platform recorded."""

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        """The last executed order of the flow that opened a position on the asset, or None if it never did."""
        ...


class ExitPlanRepositoryPort(Protocol):
    """The exit plan in force of each open position of the flows of the tenant, by flow and asset (R3.1.1).

    A plan is saved when its opening is executed and removed when the position closes, whoever closes it.
    """

    def current(self, flow_id: FlowId, asset: str) -> ExitPlan | None:
        """None when the flow has no plan in force on the asset."""
        ...

    def save(self, flow_id: FlowId, asset: str, plan: ExitPlan) -> None:
        """Replaces the plan of the flow on the asset. Raises CrossTenantAccessError for a flow of another tenant."""
        ...

    def remove(self, flow_id: FlowId, asset: str) -> None: ...


class FlowProtectionLevelsPort(Protocol):
    """Bound to the tenant of the request: the stop loss and take profit the platform keeps waiting on the exchange for
    the position of a flow, from the protections the orders context recorded (R3.1.3).
    """

    def placed_levels(self, flow_id: FlowId, asset: str) -> PlacedLevels:
        """No level where the flow has no protection of that kind in force on the asset."""
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


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    """An adapter of a source as the user asks it: no weight takes the default, a parameter not given its default."""

    name: str
    weight: int | None = None
    parameters: Mapping[str, int] = field(default_factory=dict)


class SourceCatalogPort(Protocol):
    """The sources a flow can activate, each with the adapters that offer it as they declare themselves: it is
    ListSourcesUseCase of the sources (R4.1.1, ADR fonti-con-adapter-dichiarati)."""

    def execute(self) -> SourceCatalog: ...


class ConfiguredSourceAdaptersPort(Protocol):
    """Bound to the tenant of the request: the adapters of the sources it gave credentials to (R4.1.2, ADR
    credenziali-degli-adapter-delle-fonti)."""

    def configured_adapters(self) -> frozenset[str]: ...


class SourceSettingsPort(Protocol):
    """It is SelectSourceUseCase (R1.3.1, R4.1.1, R4.1.2)."""

    def execute(self, source: str, adapters: Sequence[AdapterRequest]) -> SourceSelection:
        """The source with the adapters chosen and their parameters resolved. Raises InvalidFlowSettingError with the
        reason."""
        ...


class FlowModelsPort(Protocol):
    """The models a flow can choose, as the catalog of the platform describes them now (R1.4.2)."""

    def definition_of(self, model: str) -> ModelDefinition:
        """Raises ModelNotAvailableError or FlowModelCatalogUnavailableError."""
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


class EmergencyClosingLogPort(Protocol):
    """Bound to the tenant of the request: the emergency closings it launched, with their outcome (R3.2.3)."""

    def record(self, closing: EmergencyClosing) -> None:
        """Raises CrossTenantAccessError for a closing of another tenant."""
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


class ReferenceOpenerPort(Protocol):
    """In the worker: opens the sealed credentials of an account only for the fields a reader asks (ADR 0044)."""

    def open_reference(self, sealed: SealedAddress, names: frozenset[str]) -> AccountReference:
        """The fields named, and no other; raises FlowCredentialsNotOpenedError when the sealed text is of another
        account or no key opens it, and FlowCredentialsFieldMissingError when a field named is not in it.
        """
        ...


class CycleAccessOpenerPort(Protocol):
    def open_cycle_access(self, sealed: SealedAddress) -> CycleAccess:
        """Opens the credentials a cycle proves on the exchange; raises FlowCredentialsNotOpenedError."""
        ...


class CycleAccountReaderPort(Protocol):
    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        """Reads the account proving the credentials; raises FlowCredentialsRefusedError when the exchange refuses
        them and FlowExchangeUnavailableError when it does not answer.
        """
        ...


class ActivityReaderPort(Protocol):
    """What an exchange shows of an account: positions, balance and movements (R1.6.1)."""

    def reference_fields(self) -> frozenset[str]:
        """The names of the fields of the credentials the reader needs to find the account on its exchange."""
        ...

    def activity(self, reference: AccountReference) -> AccountActivity:
        """Raises FlowExchangeUnavailableError when the exchange cannot be read, and FlowCredentialsFieldMissingError
        when the reference lacks a field the reader declares.
        """
        ...


class AccountTransfersPort(Protocol):
    """Bound to the tenant of the request: the deposits and withdrawals the exchange declares on one of its accounts.

    Only the worker opens an account to read it on its exchange: in the API it is the client that asks the worker to
    run ReadAccountTransfersUseCase (ADR 0007, ADR storico-delle-variazioni-di-capitale).
    """

    def transfers(self, account_id: UUID, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        """Every one in the window, never part of them: raises FlowAccountNotFoundError, or
        FlowExchangeUnavailableError when the exchange cannot be read.
        """
        ...


class TransfersReaderPort(Protocol):
    """The deposits and withdrawals an exchange declares on an account (R3.4.2)."""

    def reference_fields(self) -> frozenset[str]:
        """The names of the fields of the credentials the reader needs to find the account on its exchange."""
        ...

    def transfers(self, reference: AccountReference, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        """Every one in the window. Raises FlowExchangeUnavailableError when the exchange cannot be read, and
        FlowCredentialsFieldMissingError when the reference lacks a field the reader declares.
        """
        ...


class FlowPausedNoticePort(Protocol):
    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        """Tells the user the flow paused on its own, with the reason (R1.2.4, R1.8.2)."""
        ...


class CycleFailedNoticePort(Protocol):
    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
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


class AccountDeviationThresholdPort(Protocol):
    """Bound to the tenant of the request: how far the balance of one of its accounts may go from the expected one,
    from the accounts context (R3.3.1).
    """

    def deviation_threshold(self, account_id: UUID) -> Decimal:
        """In percent of the expected balance; raises FlowAccountNotFoundError for an account the tenant does not
        have.
        """
        ...


class ReconciliationAlarmNoticePort(Protocol):
    """In the worker: NotifyReconciliationAlarmUseCase (R3.3.1)."""

    def execute(self, account_id: UUID, account_name: str, read_balance: Decimal, expected_balance: Decimal) -> None:
        """Tells the user the balance of the account is not the expected one, once for each alarm."""
        ...


@dataclass(frozen=True, slots=True)
class ReconciliationAlarmPorts:
    """What the reconciliation of an account needs to raise an alarm on its balance (R3.3.1): the threshold and the
    name of the account, and who tells the user.
    """

    thresholds: AccountDeviationThresholdPort
    accounts: FlowAccountNamePort
    notice: ReconciliationAlarmNoticePort


class UnattributablePositionNoticePort(Protocol):
    def execute(self, account_id: UUID, account_name: str, asset: str) -> None:
        """Tells the user the account holds a position no flow opened (R1.6.2)."""
        ...


class UnattributableFillNoticePort(Protocol):
    def execute(self, account_id: UUID, account_name: str, asset: str) -> None:
        """Tells the user the account shows an execution no flow ordered (R1.6.2)."""
        ...


class AccountExecutionsPort(Protocol):
    """In the worker: the executions and the funding the exchange still holds of an account since a moment (ADR 0063).

    It is ReadAccountExecutionsUseCase; the window says when part of what was asked is gone already.
    """

    def execute(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        """Raises FlowAccountNotFoundError, or FlowExchangeUnavailableError when the exchange cannot be read."""
        ...


class ExecutionsReaderPort(Protocol):
    """The executions and the funding an exchange still holds of an account since a moment (ADR 0063)."""

    def reference_fields(self) -> frozenset[str]:
        """The names of the fields of the credentials the reader needs to find the account on its exchange."""
        ...

    def since(self, reference: AccountReference, since: datetime | None) -> ExecutionsWindow:
        """Raises FlowExchangeUnavailableError when the exchange cannot be read, and FlowCredentialsFieldMissingError
        when the reference lacks a field the reader declares.
        """
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

    def record(self, account_id: UUID, ledger: AccountLedger, cursor: datetime) -> AccountLedger:
        """Records what is new and adds it to the totals of its flows in the same transaction; returns what was new,
        executions and funding.
        """
        ...

    def totals_of(self, flow_ids: Iterable[FlowId]) -> Mapping[FlowId, FlowTotals]:
        """The running totals of those flows; a flow without any execution yet has none."""
        ...


class LedgerRecordingPort(Protocol):
    """Bound to the tenant of the request: records in the ledger what the exchange added to an account (ADR 0063).

    Only the worker reads the executions of an account: in the API it is the client that asks the worker to run
    RecordAccountExecutionsUseCase (ADR 0007, ADR incasso-dei-profitti).
    """

    def record(self, account_id: UUID) -> None:
        """Raises FlowAccountNotFoundError, FlowLedgerIncompleteError, or FlowExchangeUnavailableError."""
        ...


class OnDemandCyclePort(Protocol):
    """Bound to the tenant of the request: runs a cycle of a flow now (R6.5.2, ADR
    comando-del-ciclo-su-richiesta-nell-api).

    Only the worker runs the cycles: in the API it is the client that asks the worker to run RunCycleOnDemandUseCase
    and waits for the cycle to end. A failed cycle is its record, not an error.
    """

    def run(self, flow_id: UUID) -> CycleRecord:
        """Raises FlowNotFoundError, FlowNotActiveError, CycleInProgressError, or CycleWorkerUnavailableError."""
        ...


@dataclass(frozen=True, slots=True)
class FlowAccountPorts:
    """Where a flow learns of its account: the accounts of the tenant, what the exchange shows of them now and the
    ledger of their flows, from which the free capital is measured (ADR 0087, ADR capitale-libero-al-netto-del-valore-
    dei-flussi).
    """

    directory: FlowAccountDirectoryPort
    activity: AccountActivityPort
    ledger: FlowLedgerPort


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
    """Bound to the tenant of the request: the readings of its accounts, what no flow explains (R1.6.2) and the alarms
    on their balance (R3.3.1).
    """

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

    def unattributable_of(
        self, account_id: UUID, criteria: UnattributableFilter, cursor: UnattributableCursor | None
    ) -> UnattributablePage:
        """The cases recorded for the account, open and resolved, that the filter admits: the page after the cursor,
        newest first, and the count and the net of the changes of the balance of every case of the filter, whatever
        the page (ADR movimenti-non-spiegati-nel-riquadro-del-conto).
        """
        ...

    def open_alarm(self, account_id: UUID) -> ReconciliationAlarm | None:
        """The alarm of the account still waiting for the confirmation of the user, if any."""
        ...

    def open(self, alarm: ReconciliationAlarm) -> bool:
        """Opens the alarm unless its account has one open already, also when two cycles of the account run together;
        True when it is new.
        """
        ...

    def confirm(self, account_id: UUID, at: datetime) -> bool:
        """Closes the open alarm of the account, confirmed at that moment; False when the account has none open."""
        ...

    def alarms_of(self, account_id: UUID) -> list[ReconciliationAlarm]:
        """Every alarm of the account, open and closed, the most recent first."""
        ...


class OutsideClosingRecorderPort(Protocol):
    """Bound to the tenant of the request: the history of the closed positions of its flows (R1.7.2)."""

    def execute(self, closing: OutsideClosing) -> None:
        """Records a position the reconciliation finds closed outside the platform (ADR 0056)."""
        ...


class ProtectionClosingRecorderPort(Protocol):
    """Bound to the tenant of the request: the history of the closed positions of its flows (R1.7.2)."""

    def execute(self, closing: ProtectionClosing) -> None:
        """Records a position the reconciliation finds closed by its stop loss or take profit (R3.1.2)."""
        ...


@dataclass(frozen=True, slots=True)
class ProtectedPosition:
    """The position of the account of a flow on an asset, whose protections its closing leaves behind (R3.1.2)."""

    account_id: UUID
    asset: str


class ProtectionCancellationPort(Protocol):
    """It is CancelProtectionsUseCase of the orders context, bound to the tenant of the request (R3.1.2).

    The protections left on the exchange by a closing the reconciliation finds are cancelled through the worker's own
    access to the account, as every order of a flow.
    """

    def execute(self, position: ProtectedPosition) -> None: ...


class ClosedPositionRepositoryPort(Protocol):
    """Bound to the tenant of the request."""

    def add(self, position: ClosedPosition) -> None:
        """Raises CrossTenantAccessError for a position of another tenant."""
        ...

    def matching(
        self, flow_id: FlowId, criteria: ClosedPositionFilter, offset: int, limit: int
    ) -> list[ClosedPosition]:
        """The closed positions of the flow that match the filter, from the most recent close (R6.4.4)."""
        ...

    def count(self, flow_id: FlowId, criteria: ClosedPositionFilter) -> int:
        """How many closed positions of the flow match the filter (R6.4.4)."""
        ...

    def closed_within(self, flow_id: FlowId, window: TimeWindow) -> list[ClosedPosition]:
        """The closed positions of the flow whose closing falls in the window (R2.2.6)."""
        ...


class PositionClosedNoticePort(Protocol):
    def execute(  # noqa: PLR0913, PLR0917 - the flow, by its id and name, and the closing of the position
        self, flow_id: UUID, flow_name: str, asset: str, pnl: Decimal, reason: str, closed_at: datetime
    ) -> None:
        """Tells a closing of the flow once, with the PnL its history keeps or the exchange reported (ADR 0070) and the
        reason of the closing (R3.5.1), leading to the position by its asset and the instant it closed (R3.5.6).
        """
        ...


class CashOutNoticePort(Protocol):
    def execute(self, flow_id: UUID, flow_name: str, freed: Decimal) -> None:
        """Tells the user the cash-out of the flow, with the money it freed (R3.5.1)."""
        ...


class EmergencyClosingNoticePort(Protocol):
    def execute(self, positions_closed: int, paused_flows: Sequence[str]) -> None:
        """Tells the user the emergency closing once, with the positions it closed and the flows it left paused
        (R3.5.1).
        """
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
    """The state of the flow read at the start of the cycle; the cycle only needs the adapters of its active sources.

    The state itself belongs to the flow and travels to the context and the risk check as it is (ADR 0041): its type
    is the one the composition root binds, never known to the cycles context (ADR 0082).
    """

    sources: tuple[ActiveSource, ...]
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

    The outcomes travel only to the record: approved, reduced, blocked or discarded (R1.7.1). Reversing says that the
    opening of a reversal waits for the close among the orders: the cycle checks and sends it in a second execution
    (R1.4.10).
    """

    orders: tuple[O, ...]
    outcomes: object
    reversing: bool = False


@dataclass(frozen=True, slots=True)
class ReversedExecutions[E = object]:
    """The executions of a cycle with reversals: those of the orders sent, and the outcome of the opening of every
    reversal, checked on the state of the flow after its close (R1.4.10).
    """

    executions: tuple[E, ...]
    reversals: object


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


class CycleFlowActivityPort(Protocol):
    def execute(self, flow_id: UUID) -> bool:
        """True while the flow runs cycles: read when its cycle starts, after the planner may have kept a stale job."""
        ...


class FlowLockPort(Protocol):
    def hold(self, flow_id: UUID) -> AbstractContextManager[bool]:
        """Holds the flow for one cycle, across processes; yields False at once when a cycle is still running."""
        ...


class CycleCheckpointsPort[K = object](Protocol):
    """Where the graph of a cycle keeps its checkpoints, to resume from the last node done and to debug (ADR 0104)."""

    def thread(self, flow_id: UUID, planned_at: datetime) -> str:
        """The thread of the checkpoints of one planned cycle of a flow of the tenant."""
        ...

    def opened(self) -> AbstractContextManager[K]:
        """The checkpointer of the cycles of the tenant, open for one cycle."""
        ...


@dataclass(frozen=True, slots=True)
class CycleJob:
    """The cycles of one active flow: run at every instant of its schedule (R1.2.1).

    The key changes with the tenant, the flow, the anchor and the interval: a resumed flow or a new interval is a new
    job, and the job of a flow no longer active disappears.
    """

    key: str
    schedule: CycleSchedule
    run: Callable[[], object]


class CycleSchedulerPort(Protocol):
    def keep(self, jobs: Sequence[CycleJob]) -> None:
        """Runs each job at the instants of its schedule, at once when it is new, each apart from the others so a
        slow flow never delays another; drops the jobs not given."""
        ...


class CycleStartPort[S = object](Protocol):
    def execute(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot[S]:
        """The state of the flow at the start of the cycle; the anchor is the start of its schedule."""
        ...


class CycleEndPort[S = object, E = object](Protocol):
    def execute(self, flow_id: UUID, anchor: datetime, executions: Sequence[E]) -> S:
        """Applies the executions of the cycle and gives back the state of the flow at the end of it."""
        ...


class CycleEquityPort[S = object](Protocol):
    def execute(self, flow_id: UUID, planned_at: datetime, state: S) -> None:
        """Records the equity of the flow at the cycle, from the last state of the flow the cycle read (R2.2.3)."""
        ...


class EquitySnapshotRepositoryPort(Protocol):
    """Bound to the tenant of the request or of the cycle: it never shows the equity of a flow of another tenant."""

    def record(self, snapshot: EquitySnapshot) -> None:
        """Adds the equity of a cycle; a cycle already recorded keeps its first equity (ADR 0120).

        Raises CrossTenantAccessError for the equity of a flow of another tenant.
        """
        ...

    def of_flow(self, flow_id: UUID, window: TimeWindow) -> list[EquitySnapshot]:
        """The equity of every cycle of the flow in the window, from the oldest planned instant."""
        ...


class FlowForecastsPort(Protocol):
    """Bound to the tenant of the request: the price forecasts its flows recorded, each with the actual price beside it
    once read (R1.3.5, R3.6.1).
    """

    def expired_forecasts(self, flow_id: FlowId, now: datetime) -> list[EvaluatedForecast]:
        """Every forecast of the flow whose horizon has expired by now, with its actual price or none."""
        ...


@dataclass(frozen=True, slots=True)
class SourceAsk:
    """An active source of the flow as the cycle asks it: with the parameters, the assets and the interval of the flow
    (R1.3.2, R1.3.3).
    """

    flow_id: UUID
    planned_at: datetime
    source: str
    adapter: str
    weight: int
    parameters: Mapping[str, int]
    assets: tuple[str, ...]
    cycle_minutes: int
    asked_at: datetime


class CollectedValuesPort(Protocol):
    """What an adapter of an active source collected in the cycle: each value with its asset, or the note of its
    silence."""

    @property
    def source(self) -> str: ...

    @property
    def adapter(self) -> str: ...

    @property
    def weight(self) -> int: ...

    @property
    def entries(self) -> tuple[tuple[str | None, Mapping[str, str]], ...]: ...


class SourceCollectionPort(Protocol):
    def execute(self, ask: SourceAsk) -> CollectedValuesPort:
        """Collects and records the source for the cycle; a typed error makes the source absent (R1.2.5)."""
        ...


class SourcePort[S = object, D = object](Protocol):
    def execute(self, request: SourceRequest[S], source: ActiveSource) -> D:
        """The data of one adapter of an active source; any typed error makes it absent for the cycle (R1.2.5)."""
        ...


class ContextPort[S = object, D = object, C = object](Protocol):
    def execute(
        self,
        flow_id: UUID,
        snapshot: FlowSnapshot[S],
        readings: Sequence[SourceReading[D]],
        absent: Sequence[AbsentSource],
    ) -> C:
        """The context of the agent, declaring the missing data."""
        ...


class AgentPort[C = object, A = object](Protocol):
    def execute(self, flow_id: UUID, context: C) -> A: ...


class RiskPort[S = object, A = object, O = object](Protocol):
    def execute(self, flow_id: UUID, snapshot: FlowSnapshot[S], decisions: A) -> RiskReview[O]: ...


class OrderPort[O = object, E = object](Protocol):
    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[O]) -> Sequence[E]:
        """Sends the approved orders of the cycle, closings first, and gives back their real outcomes (R1.5.5)."""
        ...


class ReversalPort[O = object, E = object](Protocol):
    def execute(
        self, flow_id: UUID, planned_at: datetime, anchor: datetime, orders: Sequence[O]
    ) -> ReversedExecutions[E]:
        """After the orders of the cycle are sent: the opening of every reversal among them checked on the state of the
        flow after its close, the approved ones sent, with their outcomes (R1.4.10).
        """
        ...


class AccountExecutionsRecorderPort(Protocol):
    def execute(self, command: RecordAccountExecutionsCommand) -> object:
        """Records in the ledger what the exchange added to the account since the last time (ADR 0063)."""
        ...


class CycleFlowReaderPort(Protocol):
    def execute(self, command: ReadCycleFlowCommand) -> CycleFlow:
        """The flow as a cycle reads it now: its account and the state attributed to it (R1.6.1)."""
        ...


class PromptMessagePort(Protocol):
    """A message the agent receives, as the record of the cycle keeps it."""

    @property
    def role(self) -> str: ...

    @property
    def content(self) -> str: ...


class AgentPromptPort(Protocol):
    """What the agent receives for the question of a cycle, as messages (R1.4.3, R1.7.1)."""

    def messages(self) -> Sequence[PromptMessagePort]: ...


class AgentActionsPort(Protocol):
    """It is ListAgentActionsUseCase: the actions the agent may take on an asset, which the system prompt names
    (R1.4.8).
    """

    def execute(self) -> Sequence[str]: ...


class AggregatedSourcePort(Protocol):
    """What several adapters of an active source say together of an asset, as the sources hand it over (R5.1.2)."""

    @property
    def source(self) -> str: ...

    @property
    def adapter(self) -> str: ...

    @property
    def weight(self) -> int: ...

    @property
    def asset(self) -> str | None: ...

    @property
    def values(self) -> Mapping[str, str]: ...


class SourceAggregatesPort(Protocol):
    """It is AggregateCycleSourcesUseCase of the sources: the aggregates the context adds to the data of the adapters of
    the active sources, such as the volumes of several exchanges (R5.1.2, ADR fonte-volumi-con-adapter-binance).
    """

    def execute(self, data: Sequence[SourceData]) -> Sequence[AggregatedSourcePort]: ...


class AgentPromptComposerPort(Protocol):
    def execute(self, question: CycleQuestion) -> AgentPromptPort:
        """Composes what the agent receives; raises an error of the agent when the question cannot be composed."""
        ...


class DecisionExitPlanPort(Protocol):
    """The exit plan the agent gave with an opening, as the agent context hands it over (R3.1.1)."""

    @property
    def target(self) -> Decimal | None: ...

    @property
    def stop(self) -> Decimal | None: ...

    @property
    def invalidation(self) -> str | None: ...


class DecisionPlanChangePort(Protocol):
    """The change of the exit plan of an open position the agent gave with an update, as the agent context hands it
    over (R3.1.3).
    """

    @property
    def target(self) -> Decimal | None: ...

    @property
    def stop(self) -> Decimal | None: ...

    @property
    def invalidation(self) -> str | None: ...

    @property
    def remove_target(self) -> bool: ...


class AgentDecisionPort(Protocol):
    """A conforming decision of the agent, turned by the risk check into what it asks; an opening carries the
    confidence of the agent (R1.4.4, R3.1.1, R3.1.3, R3.1.4).
    """

    @property
    def asset(self) -> str: ...

    @property
    def action(self) -> str:
        """The word of the action the agent took: apri, chiudi, mantieni, aggiorna or inverti (R6.5.4, R1.4.10)."""
        ...

    @property
    def reasoning(self) -> str: ...

    @property
    def confidence(self) -> int: ...

    def intent_with[O, C, H, U, R](
        self,
        opening: Callable[[str, str, Decimal, int, DecisionExitPlanPort, int], O],
        closing: Callable[[str], C],
        holding: Callable[[str], H],
        updating: Callable[[str, DecisionPlanChangePort], U],
        reversing: Callable[[str, Decimal, int, DecisionExitPlanPort, int], R],
    ) -> O | C | H | U | R: ...


class AgentResponsePort(Protocol):
    """The answer of the model as the cycle keeps it: the raw text, the decisions, the discarded and the missing."""

    @property
    def raw(self) -> str: ...

    @property
    def decisions(self) -> Sequence[AgentDecisionPort]: ...

    @property
    def discarded(self) -> Sequence[object]: ...

    @property
    def missing(self) -> Sequence[str]: ...


class ModelUsagePort(Protocol):
    @property
    def input_tokens(self) -> int: ...

    @property
    def output_tokens(self) -> int: ...


class AgentReplyPort(Protocol):
    """The answer of the agent to a cycle, with what its calls consumed and cost and how many calls it took
    (R1.4.4-R1.4.6, R1.4.9).
    """

    @property
    def response(self) -> AgentResponsePort: ...

    @property
    def usage(self) -> ModelUsagePort: ...

    @property
    def cost_usd(self) -> Decimal | None: ...

    @property
    def attempts(self) -> int: ...


class FlowAgentPort(Protocol):
    def execute(self, question: CycleQuestion) -> AgentReplyPort:
        """Asks the model of the flow, with the key of the tenant; a temporary failure of the provider is asked again
        within the decision, an answer read but not conforming never is (R1.4.5, R1.4.9).
        """
        ...


@dataclass(frozen=True, slots=True)
class CycleContext:
    """The context the agent receives in a cycle: the question of the flow and the messages composed from it."""

    flow: CycleFlow
    question: CycleQuestion
    prompt: AgentPromptPort


@dataclass(frozen=True, slots=True)
class CycleDecisions:
    """The answer of the agent to the cycle of the flow."""

    flow: CycleFlow
    reply: AgentReplyPort


class CycleOrderExecutionPort(Protocol):
    def execute(self, cycle: CycleOrders) -> Sequence[object]:
        """Sends the approved orders, closings first, and gives back the orders as recorded with their outcomes; they
        travel only to the record of the cycle (R1.5.5, R1.7.1).
        """
        ...


class FlowPausePort(Protocol):
    def execute(self, command: PauseAffectedFlowsCommand) -> object:
        """Pauses every active flow the permanent error involves, with the message of the error as reason (R1.2.4)."""
        ...


class FlowKeysPort(Protocol):
    """Bound to the tenant of the request or of the cycle: the keys of its accounts and providers that have an expiry
    (R6.2.2, ADR controllo-giornaliero-delle-scadenze)."""

    def dated_keys(self) -> tuple[FlowKey, ...]: ...


class ExpiredKeysPausePort(Protocol):
    def execute(self, command: PauseFlowsOnExpiredKeysCommand) -> bool:
        """Pauses the active flows of every expired key of the flows of the command; True when there is one (R6.2.2)."""
        ...


class CycleFailureNoticePort(Protocol):
    def execute(self, flow_id: UUID, reason: str) -> None:
        """Tells the user the cycle of the flow failed, with the message of its error (R1.8.2)."""
        ...


class ConsecutiveFailuresPort(Protocol):
    """Bound to the tenant of the flow: the failed cycles in a row, read from the recorded cycles (R3.2.4)."""

    def consecutive_failures(self, flow_id: UUID) -> int:
        """The failed cycles of the flow recorded after its last completed cycle and since it last became active; a
        skipped cycle neither counts nor breaks the series.
        """
        ...


class ConsecutiveFailuresPausePort(Protocol):
    def execute(self, flow_id: UUID, error: AutotradingError) -> object:
        """Pauses the flow when its failed cycles in a row, the one of the error included, reach its maximum
        (R3.2.4).
        """
        ...


class OpeningsSuspensionPort(Protocol):
    """Bound to the tenant of the request or of the cycle: the openings of its flows suspended for maximum loss and
    their last resume, saved beside each flow (R3.2.2).
    """

    def status(self, flow_id: UUID) -> OpeningsStatus:
        """The openings of the flow as saved; a flow never suspended nor resumed has neither."""
        ...

    def suspend(self, flow_id: UUID, suspension: OpeningsSuspension) -> None:
        """Saves the suspension of the openings of the flow, keeping their last resume."""
        ...

    def resume(self, flow_id: UUID, resumed_at: datetime) -> None:
        """Lifts the suspension of the openings of the flow and saves the instant the peak counts again from."""
        ...


class LossReferencesPort(Protocol):
    """Bound to the tenant of the cycle: the recorded equities the losses of its flows are measured from (R3.2.2)."""

    def loss_references(self, flow_id: UUID, day_start: datetime, peak_since: datetime) -> LossReferences:
        """The last equity recorded at the start of the day or before, else the first of the day, and the one highest
        once brought to the capital of now, since the instant given; the most recent among equal ones.
        """
        ...


class OpeningsSuspendedNoticePort(Protocol):
    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        """Tells the user the openings of the flow are suspended, with the threshold passed (R3.2.2, R1.8.2)."""
        ...


class OpeningReducedNoticePort(Protocol):
    def execute(
        self, flow_id: UUID, flow_name: str, asset: str, requested_margin: Decimal, approved_margin: Decimal
    ) -> None:
        """Tells the user the risk check reduced an opening of the flow, with the margin asked and the one approved
        (R3.5.1).
        """
        ...


class OpeningBlockedNoticePort(Protocol):
    def execute(self, flow_id: UUID, flow_name: str, asset: str, cause: str) -> None:
        """Tells the user the risk check blocked an opening of the flow, with its cause (R3.5.1)."""
        ...


class FlowLossGuardPort(Protocol):
    def execute(self, flow: CycleFlow) -> OpeningsSuspension | None:
        """The suspension of the openings of the flow of the cycle for maximum loss in force, suspending them when a
        threshold is passed now; None while they are not suspended (R3.2.2).
        """
        ...


@dataclass(frozen=True, slots=True)
class FailedModelCall:
    """The model calls of a decision that failed: tokens and cost when the provider reported their usage, None when
    nobody knows them (R1.4.6), with how many calls the decision tried and whether any of them went out (R1.4.9, ADR
    tentativi-del-modello-registrati-nel-ciclo).
    """

    cost: CallCost | None
    attempts: int
    sent: bool = True


class CycleJournalPort(Protocol):
    """Describes for the record what the steps produced: only the contexts behind the steps know their data."""

    def describe(self, step: CycleStep, result: object) -> Mapping[str, object]:
        """The result of the step as JSON data; a credential never appears in it (R1.7.1)."""
        ...

    def call_cost(self, decision: object) -> CallCost | None:
        """Tokens and cost of the model call behind the decision of the agent (R1.4.6)."""
        ...

    def call_attempts(self, decision: object) -> int | None:
        """How many calls the decision of the agent took, beside their cost (R1.4.9)."""
        ...

    def failed_call(self, error: AutotradingError) -> FailedModelCall | None:
        """The model calls behind the error that failed the decision of the agent; None when the error tried none
        (R1.4.6, R1.4.9, ADR costo-della-decisione-fallita-nel-registro-del-ciclo, ADR
        tentativi-del-modello-registrati-nel-ciclo).
        """

    def recorded_decisions(self, decision: object) -> tuple[RecordedDecision, ...]:
        """The decisions of the agent one by asset, as the cycle records them beside its documents (R6.5.4)."""
        ...


class CycleHistoryPort(Protocol):
    """Bound to the tenant of the request: it never shows the cycles of a flow of another tenant."""

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        """The cycles of the flow from the most recent planned instant."""
        ...

    def matching(self, flow_id: UUID, criteria: CycleFilter, offset: int, limit: int) -> list[CycleRecord]:
        """The cycles of the flow that match the filter, from the most recent planned instant (R6.4.4)."""
        ...

    def count(self, flow_id: UUID, criteria: CycleFilter) -> int:
        """How many cycles of the flow match the filter (R6.4.4)."""
        ...

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None: ...

    def failed_within(self, flow_id: UUID, window: TimeWindow) -> int:
        """How many cycles of the flow planned in the window failed (R6.4.2)."""
        ...

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        """The cost of every cycle of the flow that called the model."""
        ...

    def costs_within(self, flow_id: UUID, window: TimeWindow) -> list[CycleCost]:
        """The cost of every cycle of the flow that called the model, planned in the window (R2.2.6)."""
        ...

    def last_decided(self, flow_id: UUID) -> DecidedCycle | None:
        """The most recent completed cycle of the flow in which the agent decided, with its decisions; None without
        one (R6.5.4).
        """
        ...


class DecisionHistoryPort(Protocol):
    """Bound to the tenant of the request: it never shows the decisions of a flow of another tenant (R6.5.5)."""

    def decisions_matching(
        self, flow_id: UUID, criteria: DecisionFilter, window: TimeWindow, offset: int, limit: int
    ) -> list[DatedDecision]:
        """The decisions of the completed cycles of the flow planned in the window that match the filter, one by
        asset, from the most recent planned instant and then by asset.
        """
        ...

    def decisions_count(self, flow_id: UUID, criteria: DecisionFilter, window: TimeWindow) -> int:
        """How many decisions of the completed cycles of the flow planned in the window match the filter."""
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
    version: int


class FlowSummaryPort(Protocol):
    """It is ListFlowSummariesUseCase: the flows in use of the tenant of the request, never another tenant's."""

    def execute(self) -> list[FlowSummary]: ...


class FlowAccountNamesPort(Protocol):
    """Bound to the tenant of the request: the name of each of its accounts, as the consultation shows it."""

    def account_names(self) -> Mapping[UUID, str]: ...


class FlowDirectoryPort(Protocol):
    def exists(self, flow_id: UUID) -> bool:
        """True when the flow belongs to the tenant of the request."""
        ...


class HistoricalCyclesPort(Protocol):
    """Bound to the tenant of the request: the cycles of its flows as the history reads them (R2.5.1, ADR 0138)."""

    def cycles(self, query: HistoryQuery) -> list[CycleHistoryEntry]:
        """Up to one cycle more than the limit, newest first by planned instant then flow, after the cursor.

        The period goes by the planned instant. The version is the one in force when the cycle started, or was
        planned when it never started, since a cycle reads its configuration at its start; the asset is one of that
        version.
        """
        ...


class HistoricalClosedPositionsPort(Protocol):
    """Bound to the tenant of the request: the closed positions of its flows as the history reads them (R2.5.1)."""

    def closed_positions(self, query: HistoryQuery) -> list[ClosedPositionHistoryEntry]:
        """Up to one position more than the limit, newest first by closing instant then identifier, after the cursor.

        Period and versions go by the closing instant.
        """
        ...

    def closed_position_totals(self, query: HistoryQuery) -> ClosedPositionHistoryTotals:
        """The PnL and the fees of every position the filters admit, whatever the cursor (Bug 569)."""
        ...


class HistoricalOrdersPort(Protocol):
    """Bound to the tenant of the request: the orders sent on its accounts, with their executions (R2.5.1)."""

    def orders(self, query: HistoryQuery) -> list[OrderHistoryEntry]:
        """Up to one order more than the limit, newest first by creation instant then identifier, after the cursor.

        Period and versions go by the creation instant; a filter on the flow or the version leaves out the orders of
        no flow.
        """
        ...

    def order_totals(self, query: HistoryQuery) -> OrderHistoryTotals:
        """The fees of the executions of every order the filters admit, whatever the cursor (Bug 569)."""
        ...


class AlertResolutionPort(Protocol):
    """Bound to the tenant of the request or of the cycle: the alerts whose cause the flows remove (R6.2.3, ADR
    avvisi-nel-contesto-delle-notifiche). Nothing open to resolve is no error.
    """

    def resolve_reconciliation_alarm(self, account_id: UUID) -> None: ...

    def resolve_flow_pause(self, flow_id: FlowId) -> None: ...

    def resolve_positions_gone(self, account_id: UUID, open_assets: frozenset[str]) -> None:
        """Resolves the alerts of the positions of the account no flow explains on an asset no longer open."""
        ...
