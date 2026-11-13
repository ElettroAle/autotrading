import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from functools import partial
from uuid import UUID

import httpx

from autotrading.adapters.configuration.source import PROCESS_ENVIRONMENT, ConfigurationSource
from autotrading.adapters.inbound.api.app import ApiApplication
from autotrading.adapters.inbound.api.composition import api_adapters, worker_api_adapters
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import (
    BotPolling,
    CyclePolling,
    WorkerUseCases,
    bot_polling,
)
from autotrading.adapters.outbound.alternative_me.composition import alternative_me_adapters
from autotrading.adapters.outbound.coinmarketcap.composition import coinmarketcap_adapters
from autotrading.adapters.outbound.httpx.model_call import HttpxModelCallAdapter
from autotrading.adapters.outbound.httpx.provider_key_verifier import HttpxProviderKeyVerifierAdapter
from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_adapters, hyperliquid_slippage_adapters
from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.json.cycle_journal import JsonCycleJournalAdapter
from autotrading.adapters.outbound.json.model_catalog import load_model_catalog
from autotrading.adapters.outbound.libsodium.composition import libsodium_opening_adapters, libsodium_sealing_adapters
from autotrading.adapters.outbound.libsodium.opener import (
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.oidc.composition import oidc_adapters
from autotrading.adapters.outbound.rss.composition import rss_adapters
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.automatic_pause import SqlAlchemyAutomaticPauseAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.composition import SqlAlchemyEngine, sqlalchemy_adapters
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
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
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.agent.ask_agent import AskAgentUseCase
from autotrading.application.agent.ask_flow_agent import AskFlowAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.ports import ModelCallPort, ProviderKeyOpenerPort, ProviderKeyRepositoryPort
from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.compose_cycle_context import ComposeCycleContextUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.decide_cycle import DecideCycleUseCase
from autotrading.application.flows.end_cycle_flow import EndCycleFlowUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.application.flows.notify_unattributable import (
    NotifyUnattributableUseCase,
    UnattributableNotices,
)
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.ports import (
    AccountRemovalPorts,
    AutomaticPausePort,
    ClockPort,
    ClosedPositionRepositoryPort,
    CycleContext,
    CycleDecisions,
    CycleRepositoryPort,
    ExchangeLimitsPort,
    FlowAccountPorts,
    FlowLockPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    FlowSummary,
    FlowTimingPort,
    PlannedFlowsPort,
    SourceRequest,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import (
    ReconcileAccountUseCase,
)
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_manual_closing import RecordManualClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.review_cycle_risk import ReviewCycleRiskUseCase
from autotrading.application.flows.run_cycle import CycleGuards, CycleSteps, RunCycleUseCase
from autotrading.application.flows.run_due_cycles import RunDueCyclesUseCase
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.application.flows.source_collector import SourceCollector
from autotrading.application.flows.start_cycle_flow import StartCycleFlowUseCase
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
from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import (
    FlowOrderFollowers,
    FollowFlowOrdersUseCase,
)
from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.order_failures import answered_or_named
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
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_timing import UNSTAMPED, FlowTiming
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.order import Order, OrderOrigin, OrderSource
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP
from autotrading.domain.sources.source_catalog import SOURCE_CATALOG
from autotrading.domain.sources.source_sample import CycleReference
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Opening

PROVIDER_TIMEOUT_SECONDS = 10.0

operations = logging.getLogger("autotrading.bootstrap")


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


def cycle_sources_of(collected: Sequence[CollectedSource]) -> tuple[SourceData, ...]:
    """The data of the cycle: each collected value with the weight of its source (R1.3.2)."""
    return tuple(
        SourceData(source.source, source.weight, asset, values)
        for source in collected
        for asset, values in source.entries
    )


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


def tenant_use_cases(
    engine: SqlAlchemyEngine,
    sealers: tuple[
        Callable[[TenantId], SodiumCredentialSealerAdapter], Callable[[TenantId], SodiumProviderKeySealerAdapter]
    ],
    environment: str,
    worker_of: Callable[[TenantId], WorkerAdaptersOfTenant],
    providers: httpx.Client,
) -> Callable[[TenantId], TenantUseCases]:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""
    provider_key_verifier = HttpxProviderKeyVerifierAdapter(providers)
    credential_sealer, provider_key_sealer = sealers
    model_catalog = load_model_catalog()
    exchanges, markets, *_ = hyperliquid_adapters(ExchangeNetwork.of_installation(environment))

    def for_tenant(tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        sealer = credential_sealer(tenant_id)
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
            exchanges=exchanges,
            account_state=account_state,
            position_closing=position_closing,
            manual_closings=RecordManualClosingUseCase(flows, flow_openings, closed_positions, closing_notice),
            verification=verification,
            source_catalog=SOURCE_CATALOG,
            provider_keys=provider_keys,
            provider_key_sealer=provider_key_sealer(tenant_id),
            provider_key_verifier=provider_key_verifier,
            provider_key_usage=flows,
            model_catalog=model_catalog,
            flows=flows,
            running_verifications=SqlAlchemyRunningVerificationsAdapter(engine),
            flow_checks=FlowChecks(
                accounts=FlowAccountPorts(accounts, account_state),
                markets=markets,
                models=SelectModelUseCase(model_catalog, provider_keys),
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
            environment=environment,
        )
        return TenantUseCases.on(tenant_id, ports)

    return for_tenant


def worker_use_cases(
    engine: SqlAlchemyEngine,
    opener: SodiumCredentialOpenerAdapter,
    environment: str,
    slippage: Slippage,
    messenger: MessengerPort,
) -> Callable[[TenantId], WorkerUseCases]:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names."""
    exchanges, _, order_exchanges, activity_readers, *_ = hyperliquid_adapters(
        ExchangeNetwork.of_installation(environment)
    )

    def for_tenant(tenant_id: TenantId) -> WorkerUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, exchanges)
        close_exchange_position = CloseExchangePositionUseCase(access, order_exchanges, orders, slippage)
        open_position = OpenPositionUseCase(access, order_exchanges, orders, slippage)
        read_market = ReadMarketUseCase(access, order_exchanges)
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=close_exchange_position,
            run_exchange_verification=RunExchangeVerificationUseCase(
                VerificationReadings(
                    ReadAccountForVerificationUseCase(accounts, opener, exchanges),
                    SqlAlchemyFlowRepositoryAdapter(engine, tenant_id),
                ),
                OrderExecutionFromOrders(open_position, close_exchange_position, read_market),
                SqlAlchemyVerificationRunRepositoryAdapter(engine, tenant_id),
                environment,
                system_clock_adapters().now,
            ),
            notify=notify_for(engine, messenger, tenant_id),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, activity_readers),
        )

    return for_tenant


def cycle_ports(
    engine: SqlAlchemyEngine,
    opener: SodiumCredentialOpenerAdapter,
    environment: str,
    slippage: Slippage,
    messenger: MessengerPort,
) -> Callable[[TenantId], TenantCyclePorts]:
    """Builds, for each cycle, the adapters and use cases bound to the tenant of its flow."""
    exchanges, _, order_exchanges, activity_readers, executions_readers, *_ = hyperliquid_adapters(
        ExchangeNetwork.of_installation(environment)
    )

    def cycle_ports_for(tenant_id: TenantId) -> TenantCyclePorts:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        openings = SqlAlchemyFlowOpeningsAdapter(engine, tenant_id)
        notify = notify_for(engine, messenger, tenant_id)
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        closing_notice = NotifyPositionClosedUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
        activity = ReadAccountActivityUseCase(accounts, opener, activity_readers)
        ledger = SqlAlchemyFlowLedgerAdapter(engine, tenant_id)
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            ReadAccountExecutionsUseCase(accounts, opener, executions_readers),
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
        reconcile_for_cycle = ReconcileAccountForCycleUseCase(
            reconcile_account,
            NotifyUnattributableUseCase(
                accounts,
                UnattributableNotices(
                    NotifyUnattributablePositionUseCase(notify),
                    NotifyUnattributableFillUseCase(notify),
                    NotifyUnattributableMovementUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY),
                ),
            ),
        )
        read_cycle_flow = ReadCycleFlowUseCase(
            flows,
            SqlAlchemyFlowTimingAdapter(engine, tenant_id),
            ReadCycleAccountUseCase(accounts, accounts, opener, exchanges),
            ReadCycleFlowStateUseCase(ReadFlowStateUseCase(flows, activity, ledger), reconcile_for_cycle),
        )
        follow_flow_orders = FollowFlowOrdersUseCase(
            FlowOrderFollowers(
                NotifyOrderRejectedUseCase(notify),
                NotifyPositionOpenedUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY),
                RecordFlowClosingUseCase(flows, openings, closed_positions, closing_notice),
            )
        )
        return TenantCyclePorts(
            flows=flows,
            pause=SqlAlchemyAutomaticPauseAdapter(engine, tenant_id),
            start_cycle=StartCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            end_cycle=EndCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            provider_keys=SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id),
            forecasts=SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
            samples=SqlAlchemySampleRepositoryAdapter(engine, tenant_id),
            send_orders=SendCycleOrdersUseCase(
                ExecuteCycleOrdersUseCase(
                    ExecuteFlowOrdersUseCase(access, order_exchanges, orders, slippage), follow_flow_orders
                )
            ),
            openings=openings,
            closed_positions=closed_positions,
            follow_flow_orders=follow_flow_orders,
            flow_paused_notice=NotifyFlowPausedUseCase(notify),
            cycle_failure=NotifyCycleFailureUseCase(flows, NotifyCycleFailedUseCase(notify)),
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
            notify=notify,
        )

    return cycle_ports_for


def notify_for(engine: SqlAlchemyEngine, messenger: MessengerPort, tenant_id: TenantId) -> NotifyUseCase:
    return NotifyUseCase(SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id), messenger)


def link_stores_for(engine: SqlAlchemyEngine, tenant_id: TenantId) -> LinkStores:
    return LinkStores(
        SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
        SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
    )


def create_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> ApiApplication:
    source = ConfigurationSource(configuration)
    engine = sqlalchemy_adapters(source)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    for_tenant = tenant_use_cases(
        engine,
        libsodium_sealing_adapters(source),
        source.environment(),
        worker_adapters(source),
        httpx.Client(timeout=PROVIDER_TIMEOUT_SECONDS),
    )
    return api_adapters(source, resolve_tenant, for_tenant, oidc_adapters(source))


def create_worker_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> ApiApplication:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    source = ConfigurationSource(configuration)
    environment = source.environment()
    opener, provider_key_opener = libsodium_opening_adapters(source)
    slippage = hyperliquid_slippage_adapters(source)
    engine = sqlalchemy_adapters(source)
    messenger, inbox, start_link = telegram_adapters(source)
    for_tenant = worker_use_cases(engine, opener, environment, slippage, messenger)
    bot = bot_polling(inbox, lambda bot_inbox: telegram_bot(engine, bot_inbox, messenger))
    ports_of = cycle_ports(engine, opener, environment, slippage, messenger)
    cycles = worker_cycles(engine, ports_of, cycle_services(environment, provider_key_opener))
    return worker_api_adapters(source, for_tenant, bot, cycles, start_link)


def cycle_services(environment: str, provider_key_opener: SodiumProviderKeyOpenerAdapter) -> CycleServices:
    """The sources, the providers and the exchange of the cycles, on the network of the installation (ADR 0042)."""
    _, markets, _, _, _, prices, market = hyperliquid_adapters(ExchangeNetwork.of_installation(environment))
    return CycleServices(
        environment=environment,
        clock=system_clock_adapters(),
        catalog=load_model_catalog(),
        provider_key_opener=provider_key_opener,
        model_call=HttpxModelCallAdapter(httpx.Client()),
        sentiments={
            SENTIMENT_ALTERNATIVE_ME.name: alternative_me_adapters(),
            SENTIMENT_COINMARKETCAP.name: coinmarketcap_adapters(),
        },
        news=rss_adapters(),
        prices=prices,
        market=market,
        exchange_limits=markets,
    )


def telegram_bot(engine: SqlAlchemyEngine, inbox: BotInboxPort, messenger: MessengerPort) -> BotPolling:
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


# The cycles of the flows in the worker (ADR 0041, ADR 0042): each cycle runs on the ports of the tenant of its flow.


@dataclass(frozen=True, slots=True)
class TenantCyclePorts:
    """The adapters a cycle uses, bound to the tenant of its flow."""

    flows: FlowRepositoryPort
    pause: AutomaticPausePort
    start_cycle: StartCycleFlowUseCase
    end_cycle: EndCycleFlowUseCase
    provider_keys: ProviderKeyRepositoryPort
    forecasts: ForecastRepositoryPort
    samples: SampleRepositoryPort
    send_orders: SendCycleOrdersUseCase
    openings: FlowOpeningsPort
    closed_positions: ClosedPositionRepositoryPort
    follow_flow_orders: FollowFlowOrdersUseCase
    flow_paused_notice: NotifyFlowPausedUseCase
    cycle_failure: NotifyCycleFailureUseCase
    notify: NotifyUseCase
    settlement_currency: str


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
        return cycle_sources_of([collected])

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


type WorkerCycle = RunCycleUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, object]
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
        start=ports.start_cycle,
        sources=SourceCollector(SourcesFromSources(ports, services), ThreadPoolConcurrentCallsAdapter()),
        context=ComposeCycleContextUseCase(ComposeAgentContextUseCase(), services.clock),
        agent=DecideCycleUseCase(
            AskFlowAgentUseCase(
                ComposeAgentContextUseCase(),
                AskAgentUseCase(
                    services.catalog, ports.provider_keys, services.provider_key_opener, services.model_call
                ),
            )
        ),
        risk=ReviewCycleRiskUseCase(CheckRiskUseCase(services.exchange_limits)),
        orders=ports.send_orders,
        end=ports.end_cycle,
        journal=JsonCycleJournalAdapter(services.environment),
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


def worker_cycles(engine: SqlAlchemyEngine, ports_of: CyclePortsOf, services: CycleServices) -> CyclePolling:
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
