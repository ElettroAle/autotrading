import base64
import binascii
import logging
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import partial
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import FastAPI
from sqlalchemy import Engine

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import (
    BotPolling,
    CyclePolling,
    WorkerUseCases,
    bot_polling,
    create_worker_api,
)
from autotrading.adapters.outbound.alternative_me.composition import alternative_me_adapters
from autotrading.adapters.outbound.coinmarketcap.composition import coinmarketcap_adapters
from autotrading.adapters.outbound.httpx.model_call import HttpxModelCallAdapter
from autotrading.adapters.outbound.httpx.provider_key_verifier import HttpxProviderKeyVerifierAdapter
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
from autotrading.adapters.outbound.json.json_document import json_document
from autotrading.adapters.outbound.json.model_catalog import load_model_catalog
from autotrading.adapters.outbound.libsodium.opener import (
    InvalidPrivateCredentialsKeyError,
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError, SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.oidc.access_token_verifier import OidcAccessTokenVerifierAdapter
from autotrading.adapters.outbound.oidc.login_endpoints import OidcLoginEndpointsAdapter
from autotrading.adapters.outbound.rss.composition import rss_adapters
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
from autotrading.adapters.outbound.system_clock.composition import system_clock_adapters
from autotrading.adapters.outbound.telegram.composition import telegram_adapters
from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.adapters.outbound.threads.cycle_launcher import ThreadCycleLauncherAdapter
from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.adapters.outbound.worker.composition import WorkerAdaptersOfTenant, worker_adapters
from autotrading.application.accounts.errors import (
    CredentialsNotOpenedError,
    ExchangeRejectedCredentialsError,
)
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    ExchangePort,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.agent.ask_agent import AgentAnswer, AskAgentCommand, AskAgentUseCase
from autotrading.application.agent.ports import ModelCallPort, ProviderKeyOpenerPort, ProviderKeyRepositoryPort
from autotrading.application.flows.check_risk import CheckRiskCommand, CheckRiskUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.errors import (
    FlowCredentialsRejectedError,
)
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.application.flows.notify_unattributable import (
    NotifyUnattributableUseCase,
    UnattributableNotices,
)
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.ports import (
    AccountRemovalPorts,
    ActivityReaderPort,
    AutomaticPausePort,
    ClockPort,
    ClosedPositionRepositoryPort,
    CycleRepositoryPort,
    ExchangeLimitsPort,
    ExecutionsReaderPort,
    FlowAccountPorts,
    FlowLockPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    FlowSnapshot,
    FlowSummary,
    FlowTimingPort,
    MarketsPort,
    PlannedFlowsPort,
    RiskReview,
    SourceReading,
    SourceRequest,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
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
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_manual_closing import RecordManualClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.run_cycle import CycleGuards, CycleSteps, RunCycleUseCase
from autotrading.application.flows.run_due_cycles import RunDueCyclesUseCase
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.flows.source_collector import SourceCollector
from autotrading.application.flows.stop_flow import StopPorts
from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_unattributable_fill import NotifyUnattributableFillUseCase
from autotrading.application.notifications.notify_unattributable_movement import (
    NotifyUnattributableMovementUseCase,
)
from autotrading.application.notifications.notify_unattributable_position import (
    NotifyUnattributablePositionUseCase,
)
from autotrading.application.notifications.ports import (
    BotInboxPort,
    LinkStores,
    MessengerPort,
)
from autotrading.application.notifications.send_test_notification import SendTestNotificationUseCase
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.close_flow_position import CloseFlowPositionCommand, CloseFlowPositionUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersCommand, ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import (
    FlowOrderFollowers,
    FollowFlowOrdersCommand,
    FollowFlowOrdersUseCase,
)
from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.order_failures import answered_or_named
from autotrading.application.orders.ports import ExchangePort as OrderExchangePort
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
from autotrading.application.verification.ports import AccountReaderPort
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.accounts.position import Position
from autotrading.domain.agent.agent_context import AgentContext, FlowStateView, PositionView, SourceData
from autotrading.domain.agent.decision import TradeDirection
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_funds import CycleFunds
from autotrading.domain.flows.cycle_record import AbsentSource
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_timing import UNSTAMPED, FlowTiming
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, approved_of
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing
from autotrading.domain.flows.trade_intent import CloseIntent, HoldIntent, OpenIntent
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderSource
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.orders.slippage import Slippage
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
    readings: Mapping[str, AccountReaderPort]


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


def tenant_use_cases(
    engine: Engine,
    public_key: PublicCredentialsKey,
    exchanges: ApiExchanges,
    worker_of: Callable[[TenantId], WorkerAdaptersOfTenant],
    providers: httpx.Client,
) -> Callable[[TenantId], TenantUseCases]:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""
    provider_key_verifier = HttpxProviderKeyVerifierAdapter(providers)

    def for_tenant(tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        sealer = SodiumCredentialSealerAdapter(public_key.key, public_key.version, tenant_id)
        bot_identity, account_state, account_activity, position_closing, verification, notifier = worker_of(tenant_id)
        provider_keys = SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id)
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        flow_positions = FlowPositionsFromOrders(CloseFlowPositionUseCase(position_closing))
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        closing_notice = NotifyPositionClosedUseCase(
            notifier,
            HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        flow_openings = SqlAlchemyFlowOpeningsAdapter(engine, tenant_id)
        stop_ports = StopPorts(
            SqlAlchemyRunningCycleAdapter(engine), flow_positions, flow_openings, closed_positions, closing_notice
        )
        ports = TenantPorts(
            accounts=accounts,
            sealer=sealer,
            exchanges=exchanges.accounts,
            account_state=account_state,
            position_closing=position_closing,
            manual_closings=RecordManualClosingUseCase(flows, flow_openings, closed_positions, closing_notice),
            verification=verification,
            source_catalog=SOURCE_CATALOG,
            provider_keys=provider_keys,
            provider_key_sealer=SodiumProviderKeySealerAdapter(public_key.key, public_key.version, tenant_id),
            provider_key_verifier=provider_key_verifier,
            provider_key_usage=flows,
            model_catalog=MODEL_CATALOG,
            flows=flows,
            running_verifications=SqlAlchemyRunningVerificationsAdapter(engine),
            flow_checks=FlowChecks(
                accounts=FlowAccountPorts(accounts, account_state),
                markets=exchanges.markets,
                models=SelectModelUseCase(MODEL_CATALOG, provider_keys),
                sources=SelectSourceUseCase(SOURCE_CATALOG),
            ),
            flow_positions=flow_positions,
            stop_ports=stop_ports,
            account_removal=AccountRemovalPorts(account_state, accounts),
            account_activity=account_activity,
            flow_ledger=SqlAlchemyFlowLedgerAdapter(engine, tenant_id),
            flow_operations=SqlAlchemyFlowOperationsAdapter(engine, tenant_id),
            link_codes=SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
            bot_identity=bot_identity,
            linked_chats=SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
            clock=system_clock_adapters().now,
            closed_positions=closed_positions,
            cycle_history=SqlAlchemyCycleRepositoryAdapter(engine, tenant_id),
            flow_directory=flows,
            flow_summaries=FlowSummariesFromFlows(flows, accounts, SqlAlchemyFlowTimingAdapter(engine, tenant_id)),
            environment=exchanges.environment,
        )
        return TenantUseCases.on(tenant_id, ports)

    return for_tenant


def worker_use_cases(
    engine: Engine,
    opener: SodiumCredentialOpenerAdapter,
    exchanges: WorkerExchanges,
    settings: WorkerSettings,
    messenger: MessengerPort,
) -> Callable[[TenantId], WorkerUseCases]:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names."""

    def for_tenant(tenant_id: TenantId) -> WorkerUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        slippage = settings.slippage
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, exchanges.accounts)
        close_exchange_position = CloseExchangePositionUseCase(access, exchanges.orders, orders, slippage)
        open_position = OpenPositionUseCase(access, exchanges.orders, orders, slippage)
        read_market = ReadMarketUseCase(access, exchanges.orders)
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=close_exchange_position,
            run_exchange_verification=RunExchangeVerificationUseCase(
                VerificationReadings(
                    ReadAccountForVerificationUseCase(accounts, opener, exchanges.readings),
                    SqlAlchemyFlowRepositoryAdapter(engine, tenant_id),
                ),
                OrderExecutionFromOrders(open_position, close_exchange_position, read_market),
                SqlAlchemyVerificationRunRepositoryAdapter(engine, tenant_id),
                settings.environment,
                system_clock_adapters().now,
            ),
            notify=notify_for(engine, messenger, tenant_id),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, exchanges.activity),
        )

    return for_tenant


def cycle_ports(
    engine: Engine,
    opener: SodiumCredentialOpenerAdapter,
    exchanges: WorkerExchanges,
    settings: WorkerSettings,
    messenger: MessengerPort,
) -> Callable[[TenantId], TenantCyclePorts]:
    """Builds, for each cycle, the adapters and use cases bound to the tenant of its flow."""

    def cycle_ports_for(tenant_id: TenantId) -> TenantCyclePorts:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        slippage = settings.slippage
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        openings = SqlAlchemyFlowOpeningsAdapter(engine, tenant_id)
        notify = notify_for(engine, messenger, tenant_id)
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        closing_notice = NotifyPositionClosedUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
        activity = ReadAccountActivityUseCase(accounts, opener, exchanges.activity)
        ledger = SqlAlchemyFlowLedgerAdapter(engine, tenant_id)
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            ReadAccountExecutionsUseCase(accounts, opener, exchanges.executions),
            SqlAlchemyPlatformOrdersAdapter(engine, tenant_id),
            ledger,
        )
        reconcile_account = ReconcileAccountUseCase(
            flows,
            activity,
            SqlAlchemyReconciliationRepositoryAdapter(engine, tenant_id),
            RecordOutsideClosingUseCase(flows, openings, closed_positions, closing_notice),
            record_executions,
        )
        return TenantCyclePorts(
            flows=flows,
            pause=SqlAlchemyAutomaticPauseAdapter(engine, tenant_id),
            accounts=accounts,
            read_exchange_state=ReadExchangeStateUseCase(accounts, opener, exchanges.accounts),
            read_flow_state=ReadFlowStateUseCase(flows, activity, ledger),
            provider_keys=SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id),
            forecasts=SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
            samples=SqlAlchemySampleRepositoryAdapter(engine, tenant_id),
            execute_flow_orders=ExecuteFlowOrdersUseCase(access, exchanges.orders, orders, slippage),
            reconcile_for_cycle=ReconcileAccountForCycleUseCase(
                reconcile_account,
                NotifyUnattributableUseCase(
                    accounts,
                    UnattributableNotices(
                        NotifyUnattributablePositionUseCase(notify),
                        NotifyUnattributableFillUseCase(notify),
                        NotifyUnattributableMovementUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY),
                    ),
                ),
            ),
            openings=openings,
            closed_positions=closed_positions,
            follow_flow_orders=FollowFlowOrdersUseCase(
                FlowOrderFollowers(
                    NotifyOrderRejectedUseCase(notify),
                    NotifyPositionOpenedUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY),
                    RecordFlowClosingUseCase(flows, openings, closed_positions, closing_notice),
                )
            ),
            flow_paused_notice=NotifyFlowPausedUseCase(notify),
            cycle_failure=NotifyCycleFailureUseCase(flows, NotifyCycleFailedUseCase(notify)),
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
            notify=notify,
            timing=SqlAlchemyFlowTimingAdapter(engine, tenant_id),
        )

    return cycle_ports_for


def notify_for(engine: Engine, messenger: MessengerPort, tenant_id: TenantId) -> NotifyUseCase:
    return NotifyUseCase(SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id), messenger)


def link_stores_for(engine: Engine, tenant_id: TenantId) -> LinkStores:
    return LinkStores(
        SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
        SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
    )


def create_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    health = HealthReport(
        version=_required(configuration, "APP_VERSION"),
        environment=_environment(configuration),
    )
    network = ExchangeNetwork.of_installation(health.environment)
    engine = _database(configuration)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    for_tenant = tenant_use_cases(
        engine,
        PublicCredentialsKey(_credentials_public_key(configuration), _credentials_key_version(configuration)),
        ApiExchanges(exchanges_for(network), markets_for(network), health.environment),
        worker_adapters(_required(configuration, "WORKER_URL"), _secret(configuration, "WORKER_TOKEN_FILE")),
        httpx.Client(timeout=PROVIDER_TIMEOUT_SECONDS),
    )
    return create_api(health, resolve_tenant, for_tenant, _authentication(configuration))


def create_worker_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    environment = _environment(configuration)
    private_keys = {_credentials_key_version(configuration): _credentials_private_key(configuration)}
    opener = SodiumCredentialOpenerAdapter(private_keys)
    network = ExchangeNetwork.of_installation(environment)
    accounts = exchanges_for(network)
    exchanges = WorkerExchanges(
        accounts,
        order_exchanges_for(network),
        activity_readers_for(network),
        executions_readers_for(network),
        accounts,
    )
    settings = WorkerSettings(environment, slippage_from(configuration))
    engine = _database(configuration)
    messenger, inbox, start_link = telegram_adapters(_optional_secret(configuration, TELEGRAM_BOT_SETTING))
    for_tenant = worker_use_cases(engine, opener, exchanges, settings, messenger)
    bot = bot_polling(inbox, lambda bot_inbox: telegram_bot(engine, bot_inbox, messenger))
    ports_of = cycle_ports(engine, opener, exchanges, settings, messenger)
    cycles = worker_cycles(engine, ports_of, cycle_services(environment, private_keys))
    return create_worker_api(_secret(configuration, "WORKER_TOKEN_FILE"), for_tenant, bot, cycles, start_link)


def cycle_services(environment: str, private_keys: Mapping[int, bytes]) -> CycleServices:
    """The sources, the providers and the exchange of the cycles, on the network of the installation (ADR 0042)."""
    network = ExchangeNetwork.of_installation(environment)
    return CycleServices(
        environment=environment,
        clock=system_clock_adapters(),
        catalog=MODEL_CATALOG,
        provider_key_opener=SodiumProviderKeyOpenerAdapter(private_keys),
        model_call=HttpxModelCallAdapter(httpx.Client()),
        sentiments={
            SENTIMENT_ALTERNATIVE_ME.name: alternative_me_adapters(),
            SENTIMENT_COINMARKETCAP.name: coinmarketcap_adapters(),
        },
        news=rss_adapters(),
        prices=HyperliquidPriceHistoryAdapter.for_network(testnet=network.is_test),
        market=HyperliquidMarketDataAdapter.for_network(testnet=network.is_test),
        exchange_limits=markets_for(network),
    )


def telegram_bot(engine: Engine, inbox: BotInboxPort, messenger: MessengerPort) -> BotPolling:
    """The only bot of the platform, in long polling inside the worker: no inbound port (ADR 0035)."""
    link_chat = LinkChatUseCase(
        SqlAlchemyLinkCodeLookupAdapter(engine),
        partial(link_stores_for, engine),
        messenger,
        system_clock_adapters().now,
    )
    test_notification = SendTestNotificationUseCase(
        SqlAlchemyLinkedChatLookupAdapter(engine), partial(notify_for, engine, messenger), messenger
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
    issuer = _required(configuration, "AUTH_ISSUER")
    return Authentication(
        client_id=_required(configuration, "AUTH_CLIENT_ID"),
        scope=_required(configuration, "AUTH_SCOPE"),
        verifier=OidcAccessTokenVerifierAdapter(issuer, _required(configuration, "AUTH_AUDIENCE")),
        login=OidcLoginEndpointsAdapter(issuer),
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


# The cycles of the flows in the worker (ADR 0041, ADR 0042): each cycle runs on the ports of the tenant of its flow.


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
    reconcile_for_cycle: ReconcileAccountForCycleUseCase
    openings: FlowOpeningsPort
    closed_positions: ClosedPositionRepositoryPort
    follow_flow_orders: FollowFlowOrdersUseCase
    flow_paused_notice: NotifyFlowPausedUseCase
    cycle_failure: NotifyCycleFailureUseCase
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


class FlowStateFromFlows:
    """Bridges the flows and accounts contexts to the cycles context in the worker (ADR 0042).

    The state is read from the exchange at every cycle; a refusal of the credentials is a permanent error of the
    account, so every flow of the account pauses (R1.2.4). The account is reconciled first, so the ledger holds every
    execution the state counts (ReadCycleFlowStateUseCase).
    """

    def __init__(self, ports: TenantCyclePorts) -> None:
        self._ports = ports

    def read(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot[CycleFlow]:
        reconciled = self._ports.reconcile_for_cycle.execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        return self._snapshot(flow_id, anchor, reconciled=reconciled)

    def update(
        self,
        flow_id: UUID,
        anchor: datetime,
        executions: Sequence[object],  # noqa: ARG002 - the signature of the port
    ) -> object:
        """The state of the flow at the end of the cycle, read again from the exchange after the orders (R1.7.1)."""
        self._ports.reconcile_for_cycle.execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        return self._snapshot(flow_id, anchor, reconciled=False).state

    def _snapshot(self, flow_id: UUID, anchor: datetime, *, reconciled: bool) -> FlowSnapshot[CycleFlow]:
        ports = self._ports
        flow = ports.flows.get(FlowId(flow_id))
        started_at = ports.timing.timings().get(flow.id, UNSTAMPED).beginning(anchor)
        account = find_account(ports.accounts, AccountId(flow.account_id))
        try:
            state = ports.read_exchange_state.execute(ReadExchangeStateCommand(account.id))
        except (ExchangeRejectedCredentialsError, CredentialsNotOpenedError) as error:
            raise FlowCredentialsRejectedError(account.name.value, account.id.value) from error
        read_cycle_state = ReadCycleFlowStateUseCase(ports.read_flow_state, ports.reconcile_for_cycle)
        attributed = read_cycle_state.execute(ReadCycleFlowStateCommand(flow.id, reconciled))
        cycle_flow = CycleFlow(
            flow.tenant_id, flow, account.name.value, account.exchange.value, started_at, state, attributed
        )
        return FlowSnapshot(tuple(source.name for source in flow.configuration.sources), cycle_flow)


class SourcesFromSources:
    """Bridges the sources context to the cycles context: each active source collected with the parameters of the flow,
    recorded for the cycle and given to the agent with its weight (R1.3.2-R1.3.8, ADR 0042).
    """

    def __init__(self, ports: TenantCyclePorts, services: CycleServices) -> None:
        self._ports = ports
        self._services = services

    def collect(self, request: SourceRequest[CycleFlow], source: str) -> SourcesData:
        cycle_flow = request.snapshot.state
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
        readers = self._readers_of(configuration.cycle_interval.minutes)
        collected = CollectSourceUseCase(SOURCE_CATALOG, readers, self._ports.samples).execute(command)
        return agent_sources_of([collected])

    def _readers_of(self, cycle_minutes: int) -> dict[str, SourceReaderPort]:
        services = self._services
        readers: dict[str, SourceReaderPort] = {
            name: ReadSentimentUseCase(sentiment) for name, sentiment in services.sentiments.items()
        }
        readers[NEWS.name] = ReadNewsUseCase(services.news)
        readers[FORECAST.name] = ReadForecastUseCase(ForecastAssetUseCase(services.prices, self._ports.forecasts))
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

    def __init__(self, ports: TenantCyclePorts, services: CycleServices) -> None:
        self._ports = ports
        self._services = services

    def decide(self, flow_id: UUID, context: CycleContext) -> CycleDecisions:  # noqa: ARG002 - the signature of the port
        services = self._services
        model = context.flow.configuration.model
        use_case = AskAgentUseCase(
            services.catalog, self._ports.provider_keys, services.provider_key_opener, services.model_call
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
            tuple(
                decision.intent_with(OpenIntent.of, CloseIntent, HoldIntent)
                for decision in decisions.answer.response.decisions
            ),
            configuration.risk_policy,
            cycle_flow.risk_state(),
        )
        outcomes = CheckRiskUseCase(self._exchange_limits[cycle_flow.exchange]).execute(command)
        orders = tuple(CycleOrder(cycle_flow, outcome) for outcome in approved_of(outcomes))
        return RiskReview(orders, tuple(outcomes))


class OrdersFromOrders:
    """Bridges the approved decisions of a cycle to the orders context, on the account of the flow (R1.5.5)."""

    def __init__(self, ports: TenantCyclePorts) -> None:
        self._ports = ports

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[CycleOrder]) -> Sequence[Order]:
        approved = list(orders)
        if not approved:
            return ()
        cycle_flow = approved[0].flow
        command = ExecuteFlowOrdersCommand(
            cycle_flow.flow.account_id, flow_id, planned_at, tuple(_flow_order_of(order.outcome) for order in approved)
        )
        sent = self._ports.execute_flow_orders.execute(command)
        flow = cycle_flow.flow
        self._ports.follow_flow_orders.execute(
            FollowFlowOrdersCommand(flow.id.value, flow.name.value, planned_at, tuple(sent))
        )
        return sent


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
            return {"esiti": json_document(result.outcomes), "ordini_approvati": len(result.orders)}
        if step is CycleStep.COLLECT_SOURCES and isinstance(result, list):
            return {"fonti": [_reading_document(reading) for reading in result if isinstance(reading, SourceReading)]}
        return {"risultato": json_document(result)}

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
    return json_document(_state_view(cycle_flow))


def _reading_document(reading: SourceReading) -> dict[str, object]:
    return {"fonte": reading.source, "dati": json_document(reading.data)}


def _decisions_document(answer: AgentAnswer) -> dict[str, object]:
    response = answer.response
    return {
        "risposta": response.raw,
        "decisioni": json_document(response.decisions),
        "scartate": json_document(response.discarded),
        "mancanti": list(response.missing),
    }


type WorkerCycle = RunCycleUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, Order]
type CyclePortsOf = Callable[[TenantId], TenantCyclePorts]


def run_cycle_for(
    ports_of: CyclePortsOf,
    services: CycleServices,
    cycles_of: Callable[[TenantId], CycleRepositoryPort],
    lock: FlowLockPort,
    tenant_id: TenantId,
) -> WorkerCycle:
    """The cycle of a flow of the tenant, every step on the adapters of that tenant (ADR 0041, ADR 0042)."""
    ports = ports_of(tenant_id)
    steps = CycleSteps(
        flow_state=FlowStateFromFlows(ports),
        sources=SourceCollector(SourcesFromSources(ports, services), ThreadPoolConcurrentCallsAdapter()),
        context=ContextFromAgent(services.clock),
        agent=AgentFromAgent(ports, services),
        risk=RiskFromFlows(services.exchange_limits),
        orders=OrdersFromOrders(ports),
        journal=CycleJournalFromContexts(services.environment),
    )
    guards = CycleGuards(
        cycles=cycles_of(tenant_id),
        lock=lock,
        pause=PauseAffectedFlowsUseCase(ports.flows, ports.pause, ports.flow_paused_notice),
        clock=services.clock,
        failures=ports.cycle_failure,
    )
    return RunCycleUseCase(steps, guards)


def record_actual_prices(planned: PlannedFlowsPort, ports_of: CyclePortsOf, services: CycleServices) -> None:
    """The actual price beside every expired forecast of the tenants the worker plans for (R1.3.5)."""
    record = RecordActualPricesOfTenantsUseCase(
        services.prices, planned.tenants, lambda tenant_id: ports_of(tenant_id).forecasts
    )
    record.execute(RecordActualPricesCommand(services.clock.now()))


def worker_cycles(engine: Engine, ports_of: CyclePortsOf, services: CycleServices) -> CyclePolling:
    planned = ThreadsPlannedFlowsAdapter()
    cycles_of = partial(SqlAlchemyCycleRepositoryAdapter, engine)
    run_cycle_of = partial(run_cycle_for, ports_of, services, cycles_of, SqlAlchemyFlowLockAdapter(engine))
    run_due = RunDueCyclesUseCase(
        SqlAlchemyScheduledFlowsAdapter(engine), planned, run_cycle_of, ThreadCycleLauncherAdapter(), services.clock
    )

    def plan_round() -> None:
        run_due.execute()
        record_actual_prices(planned, ports_of, services)

    return CyclePolling(plan_round)
