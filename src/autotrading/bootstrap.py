import base64
import binascii
import logging
import os
import threading
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import FastAPI
from sqlalchemy import Engine

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import (
    AccessTokenVerifier,
    AuthenticationSettings,
    OidcLoginEndpoints,
    OidcSigningKeys,
)
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import (
    BotPolling,
    CyclePolling,
    WorkerUseCases,
    bot_polling,
    create_worker_api,
)
from autotrading.adapters.outbound.httpx.account_activity import HttpxAccountActivityAdapter
from autotrading.adapters.outbound.httpx.account_state import TIMEOUT_SECONDS as WORKER_TIMEOUT_SECONDS
from autotrading.adapters.outbound.httpx.account_state import HttpxAccountStateAdapter
from autotrading.adapters.outbound.httpx.bot_identity import HttpxWorkerBotIdentityAdapter
from autotrading.adapters.outbound.httpx.model_call import HttpxModelCallAdapter
from autotrading.adapters.outbound.httpx.news import HttpxRssNewsAdapter
from autotrading.adapters.outbound.httpx.notifications import HttpxNotificationAdapter
from autotrading.adapters.outbound.httpx.position_closing import HttpxPositionClosingAdapter
from autotrading.adapters.outbound.httpx.provider_key_verifier import HttpxProviderKeyVerifierAdapter
from autotrading.adapters.outbound.httpx.sentiment import (
    HttpxAlternativeMeSentimentAdapter,
    HttpxCoinMarketCapSentimentAdapter,
)
from autotrading.adapters.outbound.httpx.telegram_channel import telegram_channel
from autotrading.adapters.outbound.httpx.verification import HttpxVerificationAdapter
from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.adapters.outbound.json.model_catalog import load_model_catalog
from autotrading.adapters.outbound.libsodium.opener import (
    InvalidPrivateCredentialsKeyError,
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError, SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.automatic_pause import SqlAlchemyAutomaticPauseAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_openings import SqlAlchemyFlowOpeningsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_operations import SqlAlchemyFlowOperationsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_timing import SqlAlchemyFlowTimingAdapter
from autotrading.adapters.outbound.sqlalchemy.forecast_repository import SqlAlchemyForecastRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.link_code_repository import (
    SqlAlchemyLinkCodeLookupAdapter,
    SqlAlchemyLinkCodeRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import (
    SqlAlchemyLinkedChatLookupAdapter,
    SqlAlchemyLinkedChatRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.platform_orders import SqlAlchemyPlatformOrdersAdapter
from autotrading.adapters.outbound.sqlalchemy.provider_key_repository import SqlAlchemyProviderKeyRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.reconciliation_repository import SqlAlchemyReconciliationRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.running_cycle import SqlAlchemyRunningCycleAdapter
from autotrading.adapters.outbound.sqlalchemy.sample_repository import SqlAlchemySampleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.scheduling import (
    SqlAlchemyFlowLockAdapter,
    SqlAlchemyScheduledFlowsAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.verification_locks import SqlAlchemyRunningVerificationsAdapter
from autotrading.adapters.outbound.sqlalchemy.verification_run_repository import (
    SqlAlchemyVerificationRunRepositoryAdapter,
)
from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.adapters.outbound.threads.cycle_launcher import ThreadCycleLauncherAdapter
from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    CredentialsNotOpenedError,
    ExchangeRejectedCredentialsError,
)
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    CredentialOpenerPort,
    ExchangePort,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.agent.ask_agent import AgentAnswer, AskAgentCommand, AskAgentUseCase
from autotrading.application.agent.errors import (
    ProviderKeyNotFoundError,
)
from autotrading.application.agent.ports import ModelCallPort, ProviderKeyOpenerPort, ProviderKeyRepositoryPort
from autotrading.application.cycles.errors import FlowOfCycleNotFoundError
from autotrading.application.cycles.ports import (
    ClockPort,
    CycleLauncherPort,
    FlowSnapshot,
    FlowSummary,
    RiskReview,
    ScheduledFlow,
    SourceReading,
    SourceRequest,
    TenantScheduledFlow,
    TenantScheduledFlowsPort,
)
from autotrading.application.cycles.run_cycle import CycleGuards, CycleSteps, RunCycleUseCase
from autotrading.application.cycles.run_due_cycles import RunDueCyclesUseCase
from autotrading.application.cycles.source_collector import SourceCollector
from autotrading.application.flows.archive_account_flows import ArchiveAccountFlowsCommand, ArchiveAccountFlowsUseCase
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowCredentialsRejectedError,
    FlowExchangeUnavailableError,
    InvalidFlowSettingError,
)
from autotrading.application.flows.list_account_flows import ListAccountFlowsCommand, ListAccountFlowsUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand, PauseAffectedFlowsUseCase
from autotrading.application.flows.ports import (
    ActivityReaderPort,
    AutomaticPausePort,
    ClosedPositionRepositoryPort,
    ExchangeLimitsPort,
    ExecutionsReaderPort,
    FlowAccountPorts,
    FlowOpeningsPort,
    FlowRepositoryPort,
    FlowTimingPort,
    MarketsPort,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateCommand, ReadCycleFlowStateUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import (
    ReconcileAccountUseCase,
)
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingCommand, RecordFlowClosingUseCase
from autotrading.application.flows.record_manual_closing import RecordManualClosingCommand, RecordManualClosingUseCase
from autotrading.application.flows.record_outside_closing import (
    RecordOutsideClosingCommand,
    RecordOutsideClosingUseCase,
)
from autotrading.application.flows.stop_flow import StopFlowCommand, StopFlowUseCase, StopPorts
from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import (
    BotInboxPort,
    LinkStores,
    MessengerPort,
    NotifierPort,
)
from autotrading.application.notifications.send_test_notification import SendTestNotificationUseCase
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.close_flow_position import CloseFlowPositionCommand, CloseFlowPositionUseCase
from autotrading.application.orders.errors import (
    OrderAccountNotFoundError,
)
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersCommand, ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import FollowFlowOrdersCommand, FollowFlowOrdersUseCase
from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.application.orders.order_failures import answered_or_named
from autotrading.application.orders.outcome import OrderOutcome
from autotrading.application.orders.ports import ExchangePort as OrderExchangePort
from autotrading.application.orders.ports import PositionClosingPort
from autotrading.application.orders.read_market import ReadMarketCommand, ReadMarketUseCase
from autotrading.application.sources.collect_source import CollectedSource, CollectSourceCommand, CollectSourceUseCase
from autotrading.application.sources.forecast_asset import ForecastAssetUseCase
from autotrading.application.sources.ports import (
    ForecastRepositoryPort,
    MarketDataPort,
    NewsPort,
    PriceHistoryPort,
    SampleRepositoryPort,
    SentimentPort,
    SourceReaderPort,
)
from autotrading.application.sources.read_forecast import ReadForecastUseCase
from autotrading.application.sources.read_indicators import ReadIndicatorsUseCase
from autotrading.application.sources.read_news import ReadNewsUseCase
from autotrading.application.sources.read_pivots import ReadPivotsUseCase
from autotrading.application.sources.read_sentiment import ReadSentimentUseCase
from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand
from autotrading.application.sources.record_actual_prices_of_tenants import RecordActualPricesOfTenantsUseCase
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.run_exchange_verification import RunExchangeVerificationUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.accounts.position import Position
from autotrading.domain.accounts.removal import FlowPositionLeftOpen
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, PositionView, SourceData
from autotrading.domain.agent.decision import Decision, TradeAction, TradeDirection
from autotrading.domain.agent.errors import (
    ModelNotAvailableError,
    ParameterNotSupportedError,
    ParameterOutOfRangeError,
    UnknownParameterError,
)
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.cycles.call_cost import CallCost
from autotrading.domain.cycles.cycle_record import AbsentSource, CycleRecord
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.cycles.cycle_step import CycleStep
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason
from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.errors import ModelRequiredError
from autotrading.domain.flows.flow import Flow, holder_of
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_timing import UNSTAMPED, FlowTiming
from autotrading.domain.flows.ledger import ExecutionsWindow
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, approved_of
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, ModelSelection, SourceSelection
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent, TradeIntent, TradeSide
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.sources.errors import (
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    UnknownSourceParameterError,
)
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_sample import CycleReference
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Opening
from autotrading.domain.verification.reading import AccountReading, PositionReading

SUPPORTED_ENVIRONMENTS = ("dev", "prod")
DEFAULT_DATABASE_PORT = "5432"
DEFAULT_CREDENTIALS_KEY_VERSION = "1"
HYPERLIQUID = "Hyperliquid"
SLIPPAGE_SETTING = "ORDER_MAX_SLIPPAGE_PERCENT"
# The sources of the platform (R1.3.1): one added here becomes selectable in every flow.
SOURCE_CATALOG = SourceCatalog((INDICATORS, PIVOTS, FORECAST, SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP, NEWS))
# The models of the platform (R1.4.2): one added to the configuration file becomes selectable in every flow.
MODEL_CATALOG = load_model_catalog()
PROVIDER_TIMEOUT_SECONDS = 10.0
TELEGRAM_BOT_SETTING = "TELEGRAM_BOT_TOKEN_FILE"

operations = logging.getLogger("autotrading.bootstrap")


class MissingConfigurationError(AutotradingError):
    def __init__(self, name: str) -> None:
        super().__init__(f"configurazione mancante: {name}")
        self.name = name


class InvalidConfigurationError(AutotradingError):
    def __init__(self, name: str) -> None:
        super().__init__(f"configurazione non valida: {name}")
        self.name = name


class UndeclaredEnvironmentError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("ambiente non dichiarato")


class UnsupportedEnvironmentError(AutotradingError):
    def __init__(self, environment: str) -> None:
        super().__init__("ambiente non ammesso: sono ammessi " + " e ".join(SUPPORTED_ENVIRONMENTS))
        self.environment = environment


@dataclass(frozen=True, slots=True)
class PublicCredentialsKey:
    key: bytes = field(repr=False)
    version: int


@dataclass(frozen=True, slots=True)
class WorkerConnection:
    """How the API reaches the worker: its internal address and the token generated on the machine (ADR 0021)."""

    client: httpx.Client
    token: str = field(repr=False)


MODEL_REFUSALS = (ModelNotAvailableError, ParameterOutOfRangeError, ParameterNotSupportedError, UnknownParameterError)
SOURCE_REFUSALS = (SourceNotAvailableError, SourceParameterOutOfRangeError, UnknownSourceParameterError)


class FlowSummariesFromFlows:
    """Bridges the flows and accounts contexts to the consultation of the cycles (R1.7.3, ADR 0042).

    The schedule of a flow starts at its last start or resume, the anchor the database stamps on the flow.
    """

    def __init__(self, flows: FlowRepositoryPort, accounts: AccountRepositoryPort, timing: FlowTimingPort) -> None:
        self._flows = flows
        self._accounts = accounts
        self._timing = timing

    def in_use(self) -> list[FlowSummary]:
        timings = self._timing.timings()
        names = {account.id.value: account.name.value for account in self._accounts.list()}
        return [
            _summary_of(flow, names.get(flow.account_id, ""), timings.get(flow.id, UNSTAMPED))
            for flow in ListFlowsUseCase(self._flows).execute()
        ]


def _summary_of(flow: Flow, account: str, timing: FlowTiming) -> FlowSummary:
    configuration = flow.configuration
    interval = timedelta(minutes=configuration.cycle_interval.minutes)
    return FlowSummary(
        flow_id=flow.id.value,
        name=flow.name.value,
        account=account,
        status=flow.status.value,
        pause_reason=timing.pause_reason,
        model=configuration.model.name,
        schedule=CycleSchedule.planned(flow.status.runs_cycles, timing.anchor, interval),
    )


class FlowPositionsFromOrders:
    """Bridges the orders context to the flows context in the API (ADR 0055).

    The positions are closed by the worker, the only service holding the key (ADR 0023). Their margin is the one the
    exchange declares, read with the state of the flow (R1.6.1, ADR 0067).
    """

    def __init__(self, closing: CloseFlowPositionUseCase) -> None:
        self._closing = closing

    def close(self, account_id: UUID, asset: str, user_id: UserId) -> PositionClosing | None:
        report = self._closing.execute(CloseFlowPositionCommand(account_id, asset, user_id))
        fill = ClosingFill.reported(report.average_price, report.executed_at, report.fee, report.realized_pnl)
        return PositionClosing.reported(asset, found=report.found, fill=fill, refusal=report.refusal)


class ManualClosingsRecordedInFlows:
    """Bridges the manual closing of the orders context to the history of the flows context in the API (ADR 0061).

    A position closed by hand on an asset of a flow enters its history once the exchange confirms the fill; a
    closing refused or not confirmed in time leaves the position as the exchange shows it, so nothing is recorded.
    """

    def __init__(self, closing: PositionClosingPort, history: Callable[[RecordManualClosingCommand], None]) -> None:
        self._closing = closing
        self._history = history

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        outcome = self._closing.close(account_id, coin, user_id)
        fill = ClosingFill.reported(outcome.average_price, outcome.executed_at, outcome.fee, outcome.realized_pnl)
        self._history(RecordManualClosingCommand(account_id, coin, fill))
        return outcome


class AccountFlowsFromFlows:
    """Bridges the flows context to the accounts context in the API (ADR 0054): the flows that run on an account."""

    def __init__(
        self, operating: ListAccountFlowsUseCase, stop: StopFlowUseCase, archive: ArchiveAccountFlowsUseCase
    ) -> None:
        self._operating = operating
        self._stop = stop
        self._archive = archive

    def operating(self, account_id: AccountId) -> tuple[str, ...]:
        return tuple(flow.name.value for flow in self._operating_on(account_id))

    def stop(self, account_id: AccountId, user_id: UserId) -> tuple[FlowPositionLeftOpen, ...]:
        outcomes = [
            self._stop.execute(StopFlowCommand(flow.id, user_id, CloseReason.ACCOUNT_REMOVAL))
            for flow in self._operating_on(account_id)
        ]
        return tuple(
            FlowPositionLeftOpen(position.asset, position.reason)
            for outcome in outcomes
            for position in outcome.left_open
        )

    def archive(self, account_id: AccountId) -> None:
        self._archive.execute(ArchiveAccountFlowsCommand(account_id.value))

    def _operating_on(self, account_id: AccountId) -> list[Flow]:
        return self._operating.execute(ListAccountFlowsCommand(account_id.value))


class ModelSettingsFromAgent:
    """Bridges the agent context to the flows context in the API (ADR 0031).

    A model of the catalog is usable only with a registered key of its provider (R1.4.1), and only with the
    parameters it admits (R1.4.2); a refusal reaches the flow with the reason the agent context gives.
    """

    def __init__(self, catalog: ModelCatalog, keys: ProviderKeyRepositoryPort) -> None:
        self._catalog = catalog
        self._keys = keys

    def selection(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        if not model.strip():
            raise ModelRequiredError
        try:
            definition = self._catalog.find(model)
            parameters = definition.settings(requested)
        except MODEL_REFUSALS as error:
            raise InvalidFlowSettingError(str(error)) from error
        if self._keys.get(definition.provider) is None:
            raise InvalidFlowSettingError(str(ProviderKeyNotFoundError(definition.provider)))
        return ModelSelection(definition.name, parameters)


class SourceSettingsFromSources:
    """Bridges the sources context to the flows context (ADR 0031): a source of the catalog, its parameters checked."""

    def __init__(self, catalog: SourceCatalog) -> None:
        self._catalog = catalog

    def selection(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        try:
            parameters = self._catalog.find(source).settings(requested)
        except SOURCE_REFUSALS as error:
            raise InvalidFlowSettingError(str(error)) from error
        return SourceSelection(source, DEFAULT_WEIGHT if weight is None else weight, parameters)


def agent_sources_of(collected: Sequence[CollectedSource]) -> tuple[SourceData, ...]:
    """Bridges the sources context to the agent context: each collected value with the weight of its source (R1.3.2)."""
    return tuple(
        SourceData(source.source, source.weight, asset, values)
        for source in collected
        for asset, values in source.entries
    )


@dataclass(frozen=True, slots=True)
class ApiExchanges:
    """The exchanges the API checks credentials and tradable assets on, on the network of the installation."""

    accounts: Mapping[str, ExchangePort]
    markets: Mapping[str, MarketsPort]
    environment: str = "dev"


@dataclass(frozen=True, slots=True)
class WorkerExchanges:
    """The exchanges the worker reads accounts from and sends orders to, on the network of the installation."""

    accounts: Mapping[str, ExchangePort]
    orders: Mapping[str, OrderExchangePort]
    activity: Mapping[str, ActivityReaderPort]
    executions: Mapping[str, ExecutionsReaderPort]


class TradingAccessFromAccounts:
    """Bridges the accounts context to the orders context in the worker (ADR 0023).

    The account is looked up for the tenant under row level security, then opened with the private key only the
    worker holds; an account the tenant does not have is not found before anything is opened (R0.1.3).
    """

    def __init__(self, accounts: AccountRepositoryPort, opener: CredentialOpenerPort) -> None:
        self._accounts = accounts
        self._opener = opener

    def access(self, account_id: UUID) -> TradingAccess:
        try:
            account = find_account(self._accounts, AccountId(account_id))
        except AccountNotFoundError as error:
            raise OrderAccountNotFoundError from error
        credentials = self._opener.open(account)
        return TradingAccess(account.exchange.value, credentials.account_address, credentials.secret_key)


class AccountActivityFromAccounts:
    """Bridges the accounts context to the flows context in the worker (ADR 0044).

    The account is looked up for the tenant under row level security, then opened only to learn its address: the
    readings of the exchange are public and sign nothing.
    """

    def __init__(
        self, accounts: AccountRepositoryPort, opener: CredentialOpenerPort, readers: Mapping[str, ActivityReaderPort]
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def activity(self, account_id: UUID) -> AccountActivity:
        try:
            account = find_account(self._accounts, AccountId(account_id))
        except AccountNotFoundError as error:
            raise FlowAccountNotFoundError from error
        reader = self._readers.get(account.exchange.value)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.activity(self._opener.open(account).account_address)


class AccountExecutionsFromAccounts:
    """Bridges the accounts context to the ledger of the flows in the worker (ADR 0063).

    The account is opened only to learn its address: the executions of the exchange are public and sign nothing.
    """

    def __init__(
        self, accounts: AccountRepositoryPort, opener: CredentialOpenerPort, readers: Mapping[str, ExecutionsReaderPort]
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def since(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        try:
            account = find_account(self._accounts, AccountId(account_id))
        except AccountNotFoundError as error:
            raise FlowAccountNotFoundError from error
        reader = self._readers.get(account.exchange.value)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.since(self._opener.open(account).account_address, since)


class AccountReadingFromAccounts:
    """Bridges the accounts and flows contexts to the verification context in the worker (ADR 0024, ADR 0075).

    The state is read as the worker reads it for the API; a failure becomes a failed step with its message. A stopped
    flow runs no cycle, so only an active or paused flow keeps the procedure off its assets.
    """

    def __init__(self, read_exchange_state: ReadExchangeStateUseCase, flows: FlowRepositoryPort) -> None:
        self._read_exchange_state = read_exchange_state
        self._flows = flows

    def read(self, account_id: UUID) -> AccountReading:
        try:
            state = self._read_exchange_state.execute(ReadExchangeStateCommand(AccountId(account_id)))
        except AccountNotFoundError as error:
            raise VerificationAccountNotFoundError from error
        except AutotradingError as error:
            raise VerificationStepError(str(error)) from error
        return AccountReading(
            balance=state.balance.amount,
            available_margin=state.available_margin.amount,
            currency=state.balance.currency,
            positions=tuple(
                PositionReading(position.coin, position.side.value, position.size, position.leverage)
                for position in state.positions
            ),
        )

    def flow_on(self, account_id: UUID, asset: str) -> str | None:
        return holder_of(self._flows.list(), account_id, asset)


class OrderExecutionFromOrders:
    """Bridges the orders context to the verification context in the worker (ADR 0024).

    Both orders carry the origin "procedura di verifica" and the user who launched it; a failure becomes a failed
    step with its message, and an order the exchange did not execute is a failed step with the reason.
    """

    def __init__(
        self, opening: OpenPositionUseCase, closing: CloseExchangePositionUseCase, market: ReadMarketUseCase
    ) -> None:
        self._opening = opening
        self._closing = closing
        self._market = market

    def minimum_value(self, account_id: UUID, coin: str) -> Decimal:
        return _result_of(lambda: self._market.execute(ReadMarketCommand(account_id, coin))).min_order_value

    def open(self, account_id: UUID, opening: Opening, user_id: UserId) -> OrderResult:
        command = OpenPositionCommand(
            account_id=account_id,
            coin=opening.coin,
            direction=Direction(opening.side),
            leverage=opening.leverage,
            value=opening.value,
            source=_verification_source(user_id),
        )
        return _order_result(_result_of(lambda: self._opening.execute(command)))

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderResult:
        command = CloseExchangePositionCommand(account_id, coin, _verification_source(user_id))
        return _order_result(_result_of(lambda: self._closing.execute(command)))


def _verification_source(user_id: UserId) -> OrderSource:
    return OrderSource(OrderOrigin.VERIFICATION, user_id.value)


def _result_of[T](send: Callable[[], T]) -> T:
    """What the orders context answers, its failures as the verification context names them."""
    return answered_or_named(send, VerificationAccountNotFoundError, VerificationStepError)


def _order_result(order: Order) -> OrderResult:
    outcome = OrderOutcome.of(order)
    return OrderResult.reported(outcome.fee, outcome.realized_pnl, outcome.exchange_message, outcome.status.value)


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """What the installation declares to the worker beyond its secrets."""

    environment: str
    slippage: Slippage


class TenantUseCaseFactory:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""

    def __init__(
        self,
        engine: Engine,
        public_key: PublicCredentialsKey,
        exchanges: ApiExchanges,
        worker: WorkerConnection,
        providers: httpx.Client,
    ) -> None:
        self._engine = engine
        self._public_key = public_key
        self._exchanges = exchanges
        self._worker = worker
        self._provider_key_verifier = HttpxProviderKeyVerifierAdapter(providers)
        # One per installation: the username, once known, is kept across requests.
        self._bot_identity = HttpxWorkerBotIdentityAdapter(worker.client, worker.token)

    def for_tenant(self, tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        sealer = SodiumCredentialSealerAdapter(self._public_key.key, self._public_key.version, tenant_id)
        account_state = HttpxAccountStateAdapter(self._worker.client, self._worker.token, tenant_id)
        provider_keys = SqlAlchemyProviderKeyRepositoryAdapter(self._engine, tenant_id)
        flows = SqlAlchemyFlowRepositoryAdapter(self._engine, tenant_id)
        position_closing = HttpxPositionClosingAdapter(self._worker.client, self._worker.token, tenant_id)
        flow_positions = FlowPositionsFromOrders(CloseFlowPositionUseCase(position_closing))
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(self._engine, tenant_id)
        notified_closings = NotifiedClosedPositions(
            closed_positions,
            flows,
            HttpxNotificationAdapter(self._worker.client, self._worker.token, tenant_id),
            HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        flow_openings = SqlAlchemyFlowOpeningsAdapter(self._engine, tenant_id)
        stop_ports = StopPorts(
            SqlAlchemyRunningCycleAdapter(self._engine), flow_positions, flow_openings, notified_closings
        )
        ports = TenantPorts(
            accounts=accounts,
            sealer=sealer,
            exchanges=self._exchanges.accounts,
            account_state=account_state,
            position_closing=ManualClosingsRecordedInFlows(
                position_closing, RecordManualClosingUseCase(flows, flow_openings, notified_closings).execute
            ),
            verification=HttpxVerificationAdapter(self._worker.client, self._worker.token, tenant_id),
            source_catalog=SOURCE_CATALOG,
            provider_keys=provider_keys,
            provider_key_sealer=SodiumProviderKeySealerAdapter(
                self._public_key.key, self._public_key.version, tenant_id
            ),
            provider_key_verifier=self._provider_key_verifier,
            provider_key_usage=flows,
            model_catalog=MODEL_CATALOG,
            flows=flows,
            running_verifications=SqlAlchemyRunningVerificationsAdapter(self._engine),
            flow_checks=FlowChecks(
                accounts=FlowAccountPorts(accounts, account_state),
                markets=self._exchanges.markets,
                models=ModelSettingsFromAgent(MODEL_CATALOG, provider_keys),
                sources=SourceSettingsFromSources(SOURCE_CATALOG),
            ),
            flow_positions=flow_positions,
            stop_ports=stop_ports,
            account_flows=AccountFlowsFromFlows(
                ListAccountFlowsUseCase(flows),
                StopFlowUseCase(flows, stop_ports),
                ArchiveAccountFlowsUseCase(flows, ArchiveFlowUseCase(flows)),
            ),
            account_activity=HttpxAccountActivityAdapter(self._worker.client, self._worker.token, tenant_id),
            flow_ledger=SqlAlchemyFlowLedgerAdapter(self._engine, tenant_id),
            flow_operations=SqlAlchemyFlowOperationsAdapter(self._engine, tenant_id),
            link_codes=SqlAlchemyLinkCodeRepositoryAdapter(self._engine, tenant_id),
            bot_identity=self._bot_identity,
            linked_chats=SqlAlchemyLinkedChatRepositoryAdapter(self._engine, tenant_id),
            clock=now,
            closed_positions=closed_positions,
            cycle_history=SqlAlchemyCycleRepositoryAdapter(self._engine, tenant_id),
            flow_directory=flows,
            flow_summaries=FlowSummariesFromFlows(
                flows, accounts, SqlAlchemyFlowTimingAdapter(self._engine, tenant_id)
            ),
            environment=self._exchanges.environment,
        )
        return TenantUseCases.on(tenant_id, ports)


class WorkerUseCaseFactory:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names."""

    def __init__(
        self,
        engine: Engine,
        opener: SodiumCredentialOpenerAdapter,
        exchanges: WorkerExchanges,
        settings: WorkerSettings,
        messenger: MessengerPort,
    ) -> None:
        self._engine = engine
        self._opener = opener
        self._exchanges = exchanges
        self._settings = settings
        self._messenger = messenger

    def for_tenant(self, tenant_id: TenantId) -> WorkerUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(self._engine, tenant_id)
        access = TradingAccessFromAccounts(accounts, self._opener)
        slippage = self._settings.slippage
        read_exchange_state = ReadExchangeStateUseCase(accounts, self._opener, self._exchanges.accounts)
        close_exchange_position = CloseExchangePositionUseCase(access, self._exchanges.orders, orders, slippage)
        open_position = OpenPositionUseCase(access, self._exchanges.orders, orders, slippage)
        read_market = ReadMarketUseCase(access, self._exchanges.orders)
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=close_exchange_position,
            run_exchange_verification=RunExchangeVerificationUseCase(
                AccountReadingFromAccounts(
                    read_exchange_state, SqlAlchemyFlowRepositoryAdapter(self._engine, tenant_id)
                ),
                OrderExecutionFromOrders(open_position, close_exchange_position, read_market),
                SqlAlchemyVerificationRunRepositoryAdapter(self._engine, tenant_id),
                self._settings.environment,
                now,
            ),
            notify=self.notify_for(tenant_id),
            read_account_activity=ReadAccountActivityUseCase(
                AccountActivityFromAccounts(accounts, self._opener, self._exchanges.activity)
            ),
        )

    def cycle_ports_for(self, tenant_id: TenantId) -> TenantCyclePorts:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(self._engine, tenant_id)
        access = TradingAccessFromAccounts(accounts, self._opener)
        slippage = self._settings.slippage
        flows = SqlAlchemyFlowRepositoryAdapter(self._engine, tenant_id)
        openings = SqlAlchemyFlowOpeningsAdapter(self._engine, tenant_id)
        notify = self.notify_for(tenant_id)
        closed_positions = NotifiedClosedPositions(
            SqlAlchemyClosedPositionRepositoryAdapter(self._engine, tenant_id),
            flows,
            notify,
            HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        closing_notice = ClosingNoticeByNotification(notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
        activity = AccountActivityFromAccounts(accounts, self._opener, self._exchanges.activity)
        ledger = SqlAlchemyFlowLedgerAdapter(self._engine, tenant_id)
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            AccountExecutionsFromAccounts(accounts, self._opener, self._exchanges.executions),
            SqlAlchemyPlatformOrdersAdapter(self._engine, tenant_id),
            ledger,
        )
        reconcile_account = ReconcileAccountUseCase(
            flows,
            activity,
            SqlAlchemyReconciliationRepositoryAdapter(self._engine, tenant_id),
            OutsideClosingsInHistory(RecordOutsideClosingUseCase(flows, openings, closed_positions, closing_notice)),
            record_executions,
        )
        return TenantCyclePorts(
            flows=flows,
            pause=SqlAlchemyAutomaticPauseAdapter(self._engine, tenant_id),
            accounts=accounts,
            read_exchange_state=ReadExchangeStateUseCase(accounts, self._opener, self._exchanges.accounts),
            read_flow_state=ReadFlowStateUseCase(flows, activity, ledger),
            provider_keys=SqlAlchemyProviderKeyRepositoryAdapter(self._engine, tenant_id),
            forecasts=SqlAlchemyForecastRepositoryAdapter(self._engine, tenant_id),
            samples=SqlAlchemySampleRepositoryAdapter(self._engine, tenant_id),
            execute_flow_orders=ExecuteFlowOrdersUseCase(access, self._exchanges.orders, orders, slippage),
            reconcile_account=reconcile_account,
            openings=openings,
            closed_positions=closed_positions,
            record_closing=RecordFlowClosingUseCase(openings, closed_positions, closing_notice),
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
            notify=notify,
            timing=SqlAlchemyFlowTimingAdapter(self._engine, tenant_id),
        )

    def notify_for(self, tenant_id: TenantId) -> NotifyUseCase:
        return NotifyUseCase(SqlAlchemyLinkedChatRepositoryAdapter(self._engine, tenant_id), self._messenger)

    def link_stores_for(self, tenant_id: TenantId) -> LinkStores:
        return LinkStores(
            SqlAlchemyLinkCodeRepositoryAdapter(self._engine, tenant_id),
            SqlAlchemyLinkedChatRepositoryAdapter(self._engine, tenant_id),
        )


class UnconfiguredMessenger:
    """Stands for Telegram until the installation has the token of the bot: every notification is a recorded
    failure, and the flows go on (ADR 0035).
    """

    def send(self, chat_id: ChatId, text: str) -> None:  # noqa: ARG002 - the signature of the port
        raise MessageNotDeliveredError


def now() -> datetime:
    return datetime.now(UTC)


def create_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    health = HealthReport(
        version=_required(configuration, "APP_VERSION"),
        environment=_environment(configuration),
    )
    network = ExchangeNetwork.of_installation(health.environment)
    engine = _database(configuration)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    tenants = TenantUseCaseFactory(
        engine,
        PublicCredentialsKey(_credentials_public_key(configuration), _credentials_key_version(configuration)),
        ApiExchanges(exchanges_for(network), markets_for(network), health.environment),
        _worker_connection(configuration),
        httpx.Client(timeout=PROVIDER_TIMEOUT_SECONDS),
    )
    return create_api(health, resolve_tenant, tenants.for_tenant, _authentication(configuration))


def create_worker_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    environment = _environment(configuration)
    private_keys = {_credentials_key_version(configuration): _credentials_private_key(configuration)}
    opener = SodiumCredentialOpenerAdapter(private_keys)
    network = ExchangeNetwork.of_installation(environment)
    exchanges = WorkerExchanges(
        exchanges_for(network),
        order_exchanges_for(network),
        activity_readers_for(network),
        executions_readers_for(network),
    )
    settings = WorkerSettings(environment, slippage_from(configuration))
    engine = _database(configuration)
    messenger, inbox, identity = telegram_channel(
        _optional_secret(configuration, TELEGRAM_BOT_SETTING), UnconfiguredMessenger()
    )
    worker = WorkerUseCaseFactory(engine, opener, exchanges, settings, messenger)
    bot = bot_polling(inbox, lambda bot_inbox: telegram_bot(engine, worker, bot_inbox, messenger))
    cycles = worker_cycles(engine, worker.cycle_ports_for, cycle_services(environment, private_keys))
    return create_worker_api(_secret(configuration, "WORKER_TOKEN_FILE"), worker.for_tenant, bot, cycles, identity)


def cycle_services(environment: str, private_keys: Mapping[int, bytes]) -> CycleServices:
    """The sources, the providers and the exchange of the cycles, on the network of the installation (ADR 0042)."""
    public = httpx.Client(timeout=PROVIDER_TIMEOUT_SECONDS)
    network = ExchangeNetwork.of_installation(environment)
    return CycleServices(
        environment=environment,
        clock=SystemClock(),
        catalog=MODEL_CATALOG,
        provider_key_opener=SodiumProviderKeyOpenerAdapter(private_keys),
        model_call=HttpxModelCallAdapter(httpx.Client()),
        sentiments={
            SENTIMENT_ALTERNATIVE_ME.name: HttpxAlternativeMeSentimentAdapter(public),
            SENTIMENT_COINMARKETCAP.name: HttpxCoinMarketCapSentimentAdapter(public),
        },
        news=HttpxRssNewsAdapter(public),
        prices=HyperliquidPriceHistoryAdapter.for_network(testnet=network.is_test),
        market=HyperliquidMarketDataAdapter.for_network(testnet=network.is_test),
        exchange_limits=markets_for(network),
    )


def telegram_bot(
    engine: Engine, worker: WorkerUseCaseFactory, inbox: BotInboxPort, messenger: MessengerPort
) -> BotPolling:
    """The only bot of the platform, in long polling inside the worker: no inbound port (ADR 0035)."""
    link_chat = LinkChatUseCase(SqlAlchemyLinkCodeLookupAdapter(engine), worker.link_stores_for, messenger, now)
    test_notification = SendTestNotificationUseCase(
        SqlAlchemyLinkedChatLookupAdapter(engine), worker.notify_for, messenger
    )
    return BotPolling(AnswerBotMessagesUseCase(inbox, link_chat, test_notification).execute)


def exchanges_for(network: ExchangeNetwork) -> dict[str, HyperliquidExchangeAdapter]:
    return {HYPERLIQUID: HyperliquidExchangeAdapter.for_network(testnet=network.is_test)}


def markets_for(network: ExchangeNetwork) -> dict[str, HyperliquidMarketsAdapter]:
    return {HYPERLIQUID: HyperliquidMarketsAdapter.for_network(testnet=network.is_test)}


def order_exchanges_for(network: ExchangeNetwork) -> dict[str, HyperliquidOrderExchangeAdapter]:
    return {HYPERLIQUID: HyperliquidOrderExchangeAdapter.for_network(testnet=network.is_test)}


def activity_readers_for(network: ExchangeNetwork) -> dict[str, HyperliquidAccountActivityAdapter]:
    return {HYPERLIQUID: HyperliquidAccountActivityAdapter.for_network(testnet=network.is_test)}


def executions_readers_for(network: ExchangeNetwork) -> dict[str, HyperliquidAccountExecutionsAdapter]:
    return {HYPERLIQUID: HyperliquidAccountExecutionsAdapter.for_network(testnet=network.is_test)}


def slippage_from(configuration: Mapping[str, str]) -> Slippage:
    """The largest distance from the current price an order accepts: 5% unless the installation says otherwise."""
    text = configuration.get(SLIPPAGE_SETTING, "").strip()
    if not text:
        return Slippage.default()
    try:
        percent = Decimal(text)
    except InvalidOperation as error:
        raise InvalidConfigurationError(SLIPPAGE_SETTING) from error
    if not percent.is_finite():
        raise InvalidConfigurationError(SLIPPAGE_SETTING)
    return Slippage.percent(percent)


def _credentials_public_key(configuration: Mapping[str, str]) -> bytes:
    name = "CREDENTIALS_PUBLIC_KEY_FILE"
    try:
        public_key = base64.b64decode(_secret(configuration, name), validate=True)
    except binascii.Error as error:
        raise InvalidCredentialsKeyError from error
    SodiumCredentialSealerAdapter(public_key, 0, TenantId.new())  # refuses a malformed key at startup
    return public_key


def _credentials_private_key(configuration: Mapping[str, str]) -> bytes:
    try:
        return base64.b64decode(_secret(configuration, "CREDENTIALS_PRIVATE_KEY_FILE"), validate=True)
    except binascii.Error as error:
        raise InvalidPrivateCredentialsKeyError from error


def _worker_connection(configuration: Mapping[str, str]) -> WorkerConnection:
    client = httpx.Client(base_url=_required(configuration, "WORKER_URL"), timeout=WORKER_TIMEOUT_SECONDS)
    return WorkerConnection(client, _secret(configuration, "WORKER_TOKEN_FILE"))


def _credentials_key_version(configuration: Mapping[str, str]) -> int:
    return int(configuration.get("CREDENTIALS_KEY_VERSION", DEFAULT_CREDENTIALS_KEY_VERSION))


def _database(configuration: Mapping[str, str]) -> Engine:
    database = SqlAlchemyDatabaseAdapter(
        host=_required(configuration, "DATABASE_HOST"),
        port=int(configuration.get("DATABASE_PORT", DEFAULT_DATABASE_PORT)),
        name=_required(configuration, "DATABASE_NAME"),
        user=_required(configuration, "DATABASE_USER"),
        # A secret is a mounted read-only file, never an environment variable (ADR 0015).
        password=_secret(configuration, "DATABASE_PASSWORD_FILE"),
    )
    return database.engine()


def _authentication(configuration: Mapping[str, str]) -> Authentication | None:
    # Until the installation declares its identity provider, every protected function answers 503 (ADR 0016).
    if not configuration.get("AUTH_ISSUER", "").strip():
        return None
    settings = AuthenticationSettings(
        issuer=_required(configuration, "AUTH_ISSUER"),
        audience=_required(configuration, "AUTH_AUDIENCE"),
        client_id=_required(configuration, "AUTH_CLIENT_ID"),
        scope=_required(configuration, "AUTH_SCOPE"),
    )
    return Authentication(
        settings,
        AccessTokenVerifier(settings, OidcSigningKeys(settings.discovery_url)),
        OidcLoginEndpoints(settings.discovery_url),
    )


def _required(configuration: Mapping[str, str], name: str) -> str:
    value = configuration.get(name, "").strip()
    if not value:
        raise MissingConfigurationError(name)
    return value


def _secret(configuration: Mapping[str, str], name: str) -> str:
    secret = Path(_required(configuration, name)).read_text(encoding="utf-8").strip()
    if not secret:
        raise MissingConfigurationError(name)
    return secret


def _optional_secret(configuration: Mapping[str, str], name: str) -> str | None:
    """A secret the installation may not have yet: unset, missing or empty means absent, never an error."""
    location = configuration.get(name, "").strip()
    if not location or not Path(location).is_file():
        return None
    return Path(location).read_text(encoding="utf-8").strip() or None


def _environment(configuration: Mapping[str, str]) -> str:
    environment = configuration.get("APP_ENVIRONMENT", "").strip()
    if not environment:
        raise UndeclaredEnvironmentError
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise UnsupportedEnvironmentError(environment)
    return environment


# The cycles of the flows in the worker (ADR 0041, ADR 0042): the cycle names only the flow, the bridges below find
# its tenant and run each step on the ports of that tenant.


class SystemClock:
    def now(self) -> datetime:
        return now()


class FlowDirectory:
    """The tenant and the anchor of every flow the worker planned: the ports of the cycle name only the flow.

    An entry is never forgotten, so a cycle still running finds its flow after the flow is paused.
    """

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._entries: dict[UUID, TenantScheduledFlow] = {}

    def remember(self, entries: Iterable[TenantScheduledFlow]) -> None:
        with self._guard:
            self._entries.update({entry.flow.flow_id: entry for entry in entries})

    def tenant_of(self, flow_id: UUID) -> TenantId:
        return self._entry(flow_id).tenant_id

    def anchor_of(self, flow_id: UUID) -> datetime:
        return self._entry(flow_id).flow.schedule.anchor

    def tenants(self) -> set[TenantId]:
        with self._guard:
            return {entry.tenant_id for entry in self._entries.values()}

    def _entry(self, flow_id: UUID) -> TenantScheduledFlow:
        with self._guard:
            entry = self._entries.get(flow_id)
        if entry is None:
            raise FlowOfCycleNotFoundError
        return entry


class ScheduledFlowsFromFlows:
    """Bridges the flows of every tenant to the cycles context in the worker (ADR 0042)."""

    def __init__(self, source: TenantScheduledFlowsPort, directory: FlowDirectory) -> None:
        self._source = source
        self._directory = directory

    def active(self) -> list[ScheduledFlow]:
        entries = self._source.active_of_every_tenant()
        self._directory.remember(entries)
        return [entry.flow for entry in entries]


@dataclass(frozen=True, slots=True)
class TenantCyclePorts:
    """The adapters a cycle uses, bound to the tenant of its flow."""

    flows: FlowRepositoryPort
    pause: AutomaticPausePort
    accounts: AccountRepositoryPort
    read_exchange_state: ReadExchangeStateUseCase
    read_flow_state: ReadFlowStateUseCase
    provider_keys: ProviderKeyRepositoryPort
    forecasts: ForecastRepositoryPort
    samples: SampleRepositoryPort
    execute_flow_orders: ExecuteFlowOrdersUseCase
    reconcile_account: ReconcileAccountUseCase
    openings: FlowOpeningsPort
    closed_positions: ClosedPositionRepositoryPort
    record_closing: RecordFlowClosingUseCase
    notify: NotifyUseCase
    settlement_currency: str
    timing: FlowTimingPort


@dataclass(frozen=True, slots=True)
class CycleServices:
    """What every cycle shares, whatever the tenant: the clock, the models, the sources, the exchanges."""

    clock: ClockPort
    catalog: ModelCatalog
    provider_key_opener: ProviderKeyOpenerPort
    model_call: ModelCallPort
    sentiments: Mapping[str, SentimentPort]
    news: NewsPort
    prices: PriceHistoryPort
    market: MarketDataPort
    exchange_limits: Mapping[str, ExchangeLimitsPort]
    environment: str


type CyclePortsOf = Callable[[TenantId], TenantCyclePorts]


@dataclass(frozen=True, slots=True)
class CycleFlow:
    """The flow of a cycle as read at its start: whose it is, its configuration in force, its state now.

    The amounts are the state attributed to the flow, the same the user consults (R1.6.1, ADR 0062); the account
    gives only the details of the positions and the margin it has free, which no flow may go beyond.
    """

    tenant_id: TenantId
    flow: Flow
    account_name: str
    exchange: str
    started_at: datetime
    account: AccountState
    attributed: FlowState

    @property
    def configuration(self) -> FlowConfiguration:
        return self.flow.configuration

    @property
    def positions(self) -> tuple[Position, ...]:
        return self.configuration.held(self.account.positions, lambda position: position.coin)

    @property
    def available_liquidity(self) -> Decimal:
        return self._funds.available_liquidity

    @property
    def total_value(self) -> Decimal:
        return self._funds.total_value

    @property
    def return_percent(self) -> Decimal:
        return self._funds.return_percent

    @property
    def _funds(self) -> CycleFunds:
        return CycleFunds(self.attributed, self.account.available_margin.amount)

    def risk_state(self) -> RiskState:
        return RiskState(
            currency=self.account.balance.currency,
            funds=self.attributed.funds,
            available_liquidity=self.available_liquidity,
            open_assets=frozenset(position.coin for position in self.positions),
        )


def flow_of_cycle(ports: TenantCyclePorts, flow_id: UUID) -> Flow:
    return ports.flows.get(FlowId(flow_id))


class FlowStateFromFlows:
    """Bridges the flows and accounts contexts to the cycles context in the worker (ADR 0042).

    The state is read from the exchange at every cycle; a refusal of the credentials is a permanent error of the
    account, so every flow of the account pauses (R1.2.4). The account is reconciled first, so the ledger holds every
    execution the state counts (ReadCycleFlowStateUseCase).
    """

    def __init__(self, directory: FlowDirectory, ports_of: CyclePortsOf) -> None:
        self._directory = directory
        self._ports_of = ports_of

    def read(self, flow_id: UUID) -> FlowSnapshot[CycleFlow]:
        ports = self._ports_of(self._directory.tenant_of(flow_id))
        reconciled = _reconcile_for_cycle(ports).execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        return self._snapshot(flow_id, reconciled=reconciled)

    def update(self, flow_id: UUID, executions: Sequence[object]) -> object:  # noqa: ARG002 - the signature of the port
        """The state of the flow at the end of the cycle, read again from the exchange after the orders (R1.7.1)."""
        ports = self._ports_of(self._directory.tenant_of(flow_id))
        _reconcile_for_cycle(ports).execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        return self._snapshot(flow_id, reconciled=False).state

    def _snapshot(self, flow_id: UUID, *, reconciled: bool) -> FlowSnapshot[CycleFlow]:
        tenant_id = self._directory.tenant_of(flow_id)
        ports = self._ports_of(tenant_id)
        flow = flow_of_cycle(ports, flow_id)
        account = find_account(ports.accounts, AccountId(flow.account_id))
        try:
            state = ports.read_exchange_state.execute(ReadExchangeStateCommand(account.id))
        except (ExchangeRejectedCredentialsError, CredentialsNotOpenedError) as error:
            raise FlowCredentialsRejectedError(account.name.value, account.id.value) from error
        read_cycle_state = ReadCycleFlowStateUseCase(ports.read_flow_state, _reconcile_for_cycle(ports))
        attributed = read_cycle_state.execute(ReadCycleFlowStateCommand(flow.id, reconciled))
        started_at = ports.timing.timings().get(flow.id, UNSTAMPED).beginning(self._directory.anchor_of(flow_id))
        cycle_flow = CycleFlow(
            tenant_id, flow, account.name.value, account.exchange.value, started_at, state, attributed
        )
        return FlowSnapshot(tuple(source.name for source in flow.configuration.sources), cycle_flow)


def _reconcile_for_cycle(ports: TenantCyclePorts) -> ReconcileAccountForCycleUseCase:
    return ReconcileAccountForCycleUseCase(ports.reconcile_account, UnattributableNotices(ports))


class UnattributableNotices:
    """Bridges the cases no flow explains to the notifications of the tenant (R1.6.2)."""

    def __init__(self, ports: TenantCyclePorts) -> None:
        self._ports = ports

    def notice(self, items: Sequence[UnattributableItem]) -> None:
        # A position closed outside is told by the history it enters (ADR 0070): only the new cases remain.
        for item in items:
            self._ports.notify.execute(_unattributable_notification(self._ports, item))


def _unattributable_notification(ports: TenantCyclePorts, item: UnattributableItem) -> Notification:
    account = find_account(ports.accounts, AccountId(item.account_id)).name.value
    asset = item.asset or ""
    if item.kind is UnattributableKind.POSITION:
        return Notification.unattributable_position(account, asset)
    if item.kind is UnattributableKind.FILL:
        return Notification.unattributable_fill(account, asset)
    return Notification.unattributable_movement(account, Amount(item.amount, ports.settlement_currency))


class FlowPauseFromFlows:
    """Bridges a permanent error of a cycle to the flows context: the error declares the account or the provider it
    concerns, and the flows context pauses the flows involved (R1.2.4, ADR 0082).
    """

    def __init__(self, directory: FlowDirectory, ports_of: CyclePortsOf) -> None:
        self._directory = directory
        self._ports_of = ports_of

    def pause_affected_by(self, flow_id: UUID, error: AutotradingError) -> None:
        ports = self._ports_of(self._directory.tenant_of(flow_id))
        command = PauseAffectedFlowsCommand.of_error(flow_id, error)
        PauseAffectedFlowsUseCase(ports.flows, ports.pause, PausedFlowNotices(ports.notify)).execute(command)


class PausedFlowNotices:
    """Bridges the automatic pause of the flows context to the notifications of the tenant (R1.8.2)."""

    def __init__(self, notify: NotifyUseCase) -> None:
        self._notify = notify

    def paused(self, flow: Flow, reason: str) -> None:
        self._notify.execute(Notification.flow_paused(flow.name.value, reason))


class SourcesFromSources:
    """Bridges the sources context to the cycles context: each active source collected with the parameters of the flow,
    recorded for the cycle and given to the agent with its weight (R1.3.2-R1.3.8, ADR 0042).
    """

    def __init__(self, ports_of: CyclePortsOf, services: CycleServices) -> None:
        self._ports_of = ports_of
        self._services = services

    def collect(self, request: SourceRequest[CycleFlow], source: str) -> SourcesData:
        cycle_flow = request.snapshot.state
        ports = self._ports_of(cycle_flow.tenant_id)
        configuration = cycle_flow.configuration
        selection = configuration.source(source)
        command = CollectSourceCommand(
            CycleReference(request.flow_id, request.planned_at),
            selection.name,
            selection.weight,
            selection.parameters,
            configuration.assets,
            self._services.clock.now(),
        )
        readers = self._readers_of(ports, configuration.cycle_interval.minutes)
        collected = CollectSourceUseCase(SOURCE_CATALOG, readers, ports.samples).execute(command)
        return agent_sources_of([collected])

    def _readers_of(self, ports: TenantCyclePorts, cycle_minutes: int) -> dict[str, SourceReaderPort]:
        services = self._services
        readers: dict[str, SourceReaderPort] = {
            name: ReadSentimentUseCase(sentiment) for name, sentiment in services.sentiments.items()
        }
        readers[NEWS.name] = ReadNewsUseCase(services.news)
        readers[FORECAST.name] = ReadForecastUseCase(ForecastAssetUseCase(services.prices, ports.forecasts))
        readers[INDICATORS.name] = ReadIndicatorsUseCase(services.market, cycle_minutes)
        readers[PIVOTS.name] = ReadPivotsUseCase(services.market)
        return readers


type SourcesData = tuple[SourceData, ...]


@dataclass(frozen=True, slots=True)
class CycleContext:
    flow: CycleFlow
    agent_context: AgentContext


class ContextFromAgent:
    """Bridges the state of the flow and the sources to the agent context: the flow alone, never the account
    nor another flow (R1.4.3, ADR 0042).
    """

    def __init__(self, clock: ClockPort) -> None:
        self._clock = clock

    def compose(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port
        snapshot: FlowSnapshot[CycleFlow],
        readings: Sequence[SourceReading[SourcesData]],
        absent: Sequence[AbsentSource],
    ) -> CycleContext:
        cycle_flow = snapshot.state
        configuration = cycle_flow.configuration
        agent_context = AgentContext(
            instructions=configuration.instructions,
            assets=configuration.assets,
            max_leverage=configuration.risk_limits.max_leverage,
            started_at=cycle_flow.started_at,
            now=self._clock.now(),
            state=_state_view(cycle_flow),
            sources=tuple(data for reading in readings for data in reading.data),
            missing=tuple(f"{source.source}: {source.reason}" for source in absent),
        )
        return CycleContext(cycle_flow, agent_context)


def _state_view(cycle_flow: CycleFlow) -> FlowStateView:
    return FlowStateView(
        currency=cycle_flow.account.balance.currency,
        allocated_capital=cycle_flow.configuration.allocated_capital,
        funds=cycle_flow.attributed.funds,
        available_liquidity=cycle_flow.available_liquidity,
        total_value=cycle_flow.total_value,
        return_percent=cycle_flow.return_percent,
        positions=tuple(
            PositionView(
                position.coin,
                TradeDirection(position.side.value),
                position.size,
                position.leverage,
                position.entry_price,
                position.unrealized_pnl,
                position.liquidation_price,
            )
            for position in cycle_flow.positions
        ),
    )


@dataclass(frozen=True, slots=True)
class CycleDecisions:
    flow: CycleFlow
    answer: AgentAnswer


class AgentFromAgent:
    """Bridges the agent context to the cycles context: the model of the flow with the key of its tenant (R1.4.4)."""

    def __init__(self, ports_of: CyclePortsOf, services: CycleServices) -> None:
        self._ports_of = ports_of
        self._services = services

    def decide(self, flow_id: UUID, context: CycleContext) -> CycleDecisions:  # noqa: ARG002 - the signature of the port
        ports = self._ports_of(context.flow.tenant_id)
        services = self._services
        model = context.flow.configuration.model
        use_case = AskAgentUseCase(
            services.catalog, ports.provider_keys, services.provider_key_opener, services.model_call
        )
        answer = use_case.execute(AskAgentCommand(model.name, model.parameters, context.agent_context))
        return CycleDecisions(context.flow, answer)


@dataclass(frozen=True, slots=True)
class CycleOrder:
    flow: CycleFlow
    outcome: ApprovedOpening | ApprovedClose


class RiskFromFlows:
    """Bridges the decisions of the agent to the risk check of the flows context (R1.5.1-R1.5.4, ADR 0042)."""

    def __init__(self, exchange_limits: Mapping[str, ExchangeLimitsPort]) -> None:
        self._exchange_limits = exchange_limits

    def check(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port
        snapshot: FlowSnapshot[CycleFlow],  # noqa: ARG002 - the signature of the port
        decisions: CycleDecisions,
    ) -> RiskReview[CycleOrder]:
        cycle_flow = decisions.flow
        configuration = cycle_flow.configuration
        command = CheckRiskCommand(
            tuple(_intent_of(decision) for decision in decisions.answer.response.decisions),
            configuration.risk_policy,
            cycle_flow.risk_state(),
        )
        outcomes = CheckRiskUseCase(self._exchange_limits[cycle_flow.exchange]).execute(command)
        orders = tuple(CycleOrder(cycle_flow, outcome) for outcome in approved_of(outcomes))
        return RiskReview(orders, tuple(outcomes))


def _intent_of(decision: Decision) -> TradeIntent:
    opening = decision.opening
    if decision.action is TradeAction.CLOSE:
        return CloseIntent(decision.asset)
    if decision.action is TradeAction.OPEN and opening is not None:
        return OpenIntent(decision.asset, TradeSide(opening.direction.value), opening.margin_fraction, opening.leverage)
    return HoldIntent(decision.asset)


class OrdersFromOrders:
    """Bridges the approved decisions of a cycle to the orders context, on the account of the flow (R1.5.5)."""

    def __init__(self, ports_of: CyclePortsOf) -> None:
        self._ports_of = ports_of

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[CycleOrder]) -> Sequence[Order]:
        approved = list(orders)
        if not approved:
            return ()
        cycle_flow = approved[0].flow
        command = ExecuteFlowOrdersCommand(
            cycle_flow.flow.account_id, flow_id, planned_at, tuple(_flow_order_of(order.outcome) for order in approved)
        )
        ports = self._ports_of(cycle_flow.tenant_id)
        sent = ports.execute_flow_orders.execute(command)
        events = FlowOrderEvents(ports, cycle_flow.flow, planned_at)
        FollowFlowOrdersUseCase(events).execute(FollowFlowOrdersCommand(tuple(sent)))
        return sent


class FlowOrderEvents:
    """Bridges what the orders of a cycle left behind to the flow that sent them (R1.7.2, R1.8.2, ADR 0085)."""

    def __init__(self, ports: TenantCyclePorts, flow: Flow, planned_at: datetime) -> None:
        self._ports = ports
        self._flow = flow
        self._planned_at = planned_at

    def rejected(self, message: str) -> None:
        self._ports.notify.execute(Notification.order_rejected(self._flow.name.value, message))

    def opened(self, coin: str, direction: str, leverage: int, value: Decimal) -> None:
        amount = Amount(value, self._ports.settlement_currency)
        self._ports.notify.execute(
            Notification.position_opened(self._flow.name.value, coin, direction, leverage, amount)
        )

    def closed(self, coin: str, execution: Execution) -> None:
        command = RecordFlowClosingCommand(
            self._flow,
            coin,
            execution.average_price,
            execution.executed_at,
            execution.fee,
            execution.realized_pnl,
            self._planned_at,
        )
        self._ports.record_closing.execute(command)


def _flow_order_of(outcome: ApprovedOpening | ApprovedClose) -> FlowOrder:
    return outcome.order_with(_flow_opening_of, FlowClosing)


def _flow_opening_of(asset: str, side: str, value: Decimal, leverage: int) -> FlowOrder:
    return FlowOpening(asset, Direction(side), value, leverage)


class CycleJournalFromContexts:
    """Describes for the record what each step produced, with the data of the context behind it (R1.7.1, ADR 0042).

    Only the types of the cycle travel here: none of them carries a credential or a provider key.
    """

    def __init__(self, environment: str) -> None:
        self._environment = environment

    def describe(self, step: CycleStep, result: object) -> Mapping[str, object]:
        if isinstance(result, CycleFlow):
            return self._flow_of(result) if step is CycleStep.READ_FLOW_STATE else {"stato": _state_document(result)}
        if isinstance(result, CycleContext):
            messages = result.agent_context.messages()
            return {"messaggi": [{"ruolo": message.role.value, "contenuto": message.content} for message in messages]}
        if isinstance(result, CycleDecisions):
            return _decisions_document(result.answer)
        if isinstance(result, RiskReview):
            return {"esiti": json_of(result.outcomes), "ordini_approvati": len(result.orders)}
        if step is CycleStep.COLLECT_SOURCES and isinstance(result, list):
            return {"fonti": [_reading_document(reading) for reading in result if isinstance(reading, SourceReading)]}
        return {"risultato": json_of(result)}

    def call_cost(self, decision: object) -> CallCost | None:
        if not isinstance(decision, CycleDecisions):
            return None
        usage = decision.answer.usage
        return CallCost(usage.input_tokens, usage.output_tokens, decision.answer.cost_usd)

    def _flow_of(self, cycle_flow: CycleFlow) -> dict[str, object]:
        configuration = cycle_flow.configuration
        return {
            "utente": str(cycle_flow.tenant_id.value),
            "flusso": cycle_flow.flow.name.value,
            "conto": cycle_flow.account_name,
            "exchange": cycle_flow.exchange,
            "ambiente": self._environment,
            "versione": configuration.version,
            "fornitore": configuration.model.name.partition("/")[0],
            "modello": configuration.model.name,
            "pesi_fonti": {source.name: source.weight for source in configuration.sources},
            "stato": _state_document(cycle_flow),
        }


def _state_document(cycle_flow: CycleFlow) -> object:
    return json_of(_state_view(cycle_flow))


def _reading_document(reading: SourceReading) -> dict[str, object]:
    return {"fonte": reading.source, "dati": json_of(reading.data)}


def _decisions_document(answer: AgentAnswer) -> dict[str, object]:
    response = answer.response
    return {
        "risposta": response.raw,
        "decisioni": json_of(response.decisions),
        "scartate": json_of(response.discarded),
        "mancanti": list(response.missing),
    }


def json_of(value: object) -> object:
    """The value as JSON data: the record of a cycle keeps what each step produced as it was (R1.7.1)."""
    if value is None or isinstance(value, (bool, int, str, Decimal, UUID, datetime, Enum)):
        return _scalar_of(value)
    if isinstance(value, Mapping):
        return {str(key): json_of(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, frozenset, set)):
        return [json_of(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        document: dict[str, object] = {"tipo": type(value).__name__}
        document.update({each.name: json_of(getattr(value, each.name)) for each in fields(value)})
        return document
    return str(value)


def _scalar_of(value: object) -> object:
    if isinstance(value, Enum):
        return json_of(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value


class OutsideClosingsInHistory:
    """Bridges a position the reconciliation finds closed outside the platform to the history of the flow (ADR 0056)."""

    def __init__(self, record: RecordOutsideClosingUseCase) -> None:
        self._record = record

    def add_closed_outside(self, closing: OutsideClosing) -> None:
        self._record.execute(RecordOutsideClosingCommand(closing))


class ClosingNoticeByNotification:
    """Tells a closing with no history to enter through the notifications, in the currency of the exchange."""

    def __init__(self, notifier: NotifierPort, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def tell(self, flow: Flow, asset: str, realized_pnl: Decimal) -> None:
        pnl = Amount(realized_pnl, self._currency)
        self._notifier.execute(Notification.position_closed(flow.name.value, asset, pnl))


class NotifiedClosedPositions:
    """Tells every position that enters the history of a flow, whatever closed it, once (R1.8.2, ADR 0070).

    The notification carries the PnL the history keeps, so the user reads the same result in both.
    """

    def __init__(
        self, history: ClosedPositionRepositoryPort, flows: FlowRepositoryPort, notifier: NotifierPort, currency: str
    ) -> None:
        self._history = history
        self._flows = flows
        self._notifier = notifier
        self._currency = currency

    def add(self, position: ClosedPosition) -> None:
        self._history.add(position)
        flow = self._flows.get(position.flow_id)
        pnl = Amount(position.pnl, self._currency)
        notification = Notification.position_closed(flow.name.value, position.asset, pnl)
        self._notifier.execute(notification)

    def of_flow(self, flow_id: FlowId) -> list[ClosedPosition]:
        return self._history.of_flow(flow_id)


class CycleFailureNotices:
    """Bridges a failed cycle to the notifications of the tenant of its flow (R1.8.2)."""

    def __init__(self, directory: FlowDirectory, ports_of: CyclePortsOf) -> None:
        self._directory = directory
        self._ports_of = ports_of

    def failed(self, flow_id: UUID, reason: str) -> None:
        ports = self._ports_of(self._directory.tenant_of(flow_id))
        ports.notify.execute(Notification.cycle_failed(flow_of_cycle(ports, flow_id).name.value, reason))


class CyclesOfTenants:
    """The cycles of the flows the worker plans, each recorded in the tenant of its flow (ADR 0042, ADR 0046)."""

    def __init__(self, engine: Engine, directory: FlowDirectory) -> None:
        self._engine = engine
        self._directory = directory

    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        return self._of(flow_id).claim(flow_id, planned_at)

    def record(self, record: CycleRecord) -> None:
        self._of(record.flow_id).record(record)

    def _of(self, flow_id: UUID) -> SqlAlchemyCycleRepositoryAdapter:
        return SqlAlchemyCycleRepositoryAdapter(self._engine, self._directory.tenant_of(flow_id))


@dataclass(frozen=True, slots=True)
class CycleRuntime:
    """Where the worker finds the flows to plan, what keeps each cycle unique and alone, and how a cycle runs."""

    scheduled: TenantScheduledFlowsPort
    guards: CycleGuards
    launcher: CycleLauncherPort


type WorkerCycles = RunDueCyclesUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, Order]


def run_due_cycles(
    directory: FlowDirectory, ports_of: CyclePortsOf, services: CycleServices, runtime: CycleRuntime
) -> WorkerCycles:
    """The cycles of every active flow, each step on the ports of the tenant of its flow (ADR 0041, ADR 0042)."""
    steps = CycleSteps(
        flow_state=FlowStateFromFlows(directory, ports_of),
        sources=SourceCollector(SourcesFromSources(ports_of, services), ThreadPoolConcurrentCallsAdapter()),
        context=ContextFromAgent(services.clock),
        agent=AgentFromAgent(ports_of, services),
        risk=RiskFromFlows(services.exchange_limits),
        orders=OrdersFromOrders(ports_of),
        journal=CycleJournalFromContexts(services.environment),
    )
    flows = ScheduledFlowsFromFlows(runtime.scheduled, directory)
    return RunDueCyclesUseCase(flows, RunCycleUseCase(steps, runtime.guards), runtime.launcher, services.clock)


def record_actual_prices(directory: FlowDirectory, ports_of: CyclePortsOf, services: CycleServices) -> None:
    """The actual price beside every expired forecast of the tenants the worker plans for (R1.3.5)."""
    record = RecordActualPricesOfTenantsUseCase(
        services.prices, directory.tenants, lambda tenant_id: ports_of(tenant_id).forecasts
    )
    record.execute(RecordActualPricesCommand(services.clock.now()))


def worker_cycles(engine: Engine, ports_of: CyclePortsOf, services: CycleServices) -> CyclePolling:
    directory = FlowDirectory()
    guards = CycleGuards(
        cycles=CyclesOfTenants(engine, directory),
        lock=SqlAlchemyFlowLockAdapter(engine),
        pause=FlowPauseFromFlows(directory, ports_of),
        clock=services.clock,
        failures=CycleFailureNotices(directory, ports_of),
    )
    runtime = CycleRuntime(SqlAlchemyScheduledFlowsAdapter(engine), guards, ThreadCycleLauncherAdapter())
    run_due = run_due_cycles(directory, ports_of, services, runtime)

    def plan_round() -> None:
        run_due.execute()
        record_actual_prices(directory, ports_of, services)

    return CyclePolling(plan_round)
