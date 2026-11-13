from collections.abc import Callable, Mapping
from functools import partial

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
from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_adapters, hyperliquid_slippage_adapters
from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.json.cycle_journal import JsonCycleJournalAdapter
from autotrading.adapters.outbound.libsodium.composition import libsodium_opening_adapters, libsodium_sealing_adapters
from autotrading.adapters.outbound.libsodium.opener import (
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.litellm.composition import litellm_adapters
from autotrading.adapters.outbound.oidc.composition import oidc_adapters
from autotrading.adapters.outbound.rss.composition import rss_adapters
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.automatic_pause import SqlAlchemyAutomaticPauseAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.composition import SqlAlchemyEngine, sqlalchemy_adapters
from autotrading.adapters.outbound.sqlalchemy.cycle_checkpoints import SqlAlchemyCycleCheckpointsAdapter
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
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.agent.ask_agent import AskAgentUseCase
from autotrading.application.agent.ask_flow_agent import AskFlowAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.ports import (
    ModelCallPort,
    ModelCatalogPort,
)
from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.compose_cycle_context import ComposeCycleContextUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.cycle_graph import CycleGraph, CycleSteps
from autotrading.application.flows.decide_cycle import DecideCycleUseCase
from autotrading.application.flows.end_cycle_flow import EndCycleFlowUseCase
from autotrading.application.flows.list_flow_summaries import ListFlowSummariesUseCase
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.application.flows.notify_unattributable import (
    NotifyUnattributableUseCase,
    UnattributableNotices,
)
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.ports import (
    AccountRemovalPorts,
    CycleContext,
    CycleDecisions,
    FlowAccountPorts,
    FlowModelsPort,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateUseCase
from autotrading.application.flows.read_cycle_source import ReadCycleSourceUseCase
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
from autotrading.application.flows.run_cycle import CycleGuards, RunCycleUseCase
from autotrading.application.flows.run_due_cycles import RunDueCyclesUseCase
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
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
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.close_flow_position import CloseFlowPositionUseCase
from autotrading.application.orders.close_verification_position import CloseVerificationPositionUseCase
from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import (
    FlowOrderFollowers,
    FollowFlowOrdersUseCase,
)
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.open_verification_position import OpenVerificationPositionUseCase
from autotrading.application.orders.order_failures import FailureNames
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.orders.read_minimum_value import ReadMinimumValueUseCase
from autotrading.application.sources.collect_cycle_source import CollectCycleSourceUseCase, SourceSystems
from autotrading.application.sources.ports import SentimentPort
from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand
from autotrading.application.sources.record_actual_prices_of_tenants import RecordActualPricesOfTenantsUseCase
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.ports import ProcedureOrders
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP
from autotrading.domain.sources.source_catalog import SOURCE_CATALOG
from autotrading.domain.tenancy.tenant_id import TenantId


def tenant_use_cases(
    engine: SqlAlchemyEngine,
    sealers: tuple[
        Callable[[TenantId], SodiumCredentialSealerAdapter], Callable[[TenantId], SodiumProviderKeySealerAdapter]
    ],
    environment: str,
    worker_of: Callable[[TenantId], WorkerAdaptersOfTenant],
    providers: tuple[ModelCatalogPort, FlowModelsPort],
) -> Callable[[TenantId], TenantUseCases]:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""
    model_catalog, flow_models = providers
    credential_sealer, provider_key_sealer = sealers
    exchanges, markets, *_ = hyperliquid_adapters(ExchangeNetwork.of_installation(environment))

    def for_tenant(tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        sealer = credential_sealer(tenant_id)
        bot_identity, account_state, account_activity, position_closing, verification, notifier = worker_of(tenant_id)
        provider_keys = SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id)
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        flow_positions = CloseFlowPositionUseCase(position_closing)
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
            provider_key_usage=flows,
            model_catalog=model_catalog,
            flows=flows,
            running_verifications=SqlAlchemyRunningVerificationsAdapter(engine),
            flow_checks=FlowChecks(
                accounts=FlowAccountPorts(accounts, account_state),
                markets=markets,
                models=SelectModelUseCase(flow_models, provider_keys),
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
            flow_summaries=ListFlowSummariesUseCase(flows, accounts, SqlAlchemyFlowTimingAdapter(engine, tenant_id)),
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

    verification_failures = FailureNames(VerificationAccountNotFoundError, VerificationStepError)

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
                ProcedureOrders(
                    ReadMinimumValueUseCase(read_market, verification_failures),
                    OpenVerificationPositionUseCase(open_position, verification_failures),
                    CloseVerificationPositionUseCase(close_exchange_position, verification_failures),
                ),
                SqlAlchemyVerificationRunRepositoryAdapter(engine, tenant_id),
                environment,
                system_clock_adapters().now,
            ),
            notify=notify_for(engine, messenger, tenant_id),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, activity_readers),
        )

    return for_tenant


def cycle_of(
    engine: SqlAlchemyEngine,
    openers: tuple[SodiumCredentialOpenerAdapter, SodiumProviderKeyOpenerAdapter],
    trading: tuple[str, Slippage],
    messenger: MessengerPort,
    models: tuple[ModelCallPort, ModelCatalogPort],
) -> Callable[[TenantId], WorkerCycle]:
    """Builds, for each cycle, its graph on the adapters bound to the tenant of its flow (ADR 0042, ADR 0104).

    The clock, the models, the sources and the exchanges are the same for every tenant.
    """
    environment, slippage = trading
    model_call, catalog = models
    opener, provider_key_opener = openers
    exchanges, markets, order_exchanges, activity_readers, executions_readers, prices, market = hyperliquid_adapters(
        ExchangeNetwork.of_installation(environment)
    )
    clock = system_clock_adapters()
    sentiments: Mapping[str, SentimentPort] = {
        SENTIMENT_ALTERNATIVE_ME.name: alternative_me_adapters(),
        SENTIMENT_COINMARKETCAP.name: coinmarketcap_adapters(),
    }
    news = rss_adapters()
    lock = SqlAlchemyFlowLockAdapter(engine)

    def cycle_for(tenant_id: TenantId) -> WorkerCycle:
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
        steps = CycleSteps(
            start=StartCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            sources=ReadCycleSourceUseCase(
                CollectCycleSourceUseCase(
                    SOURCE_CATALOG,
                    SourceSystems(sentiments, news, prices, market),
                    SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
                    SqlAlchemySampleRepositoryAdapter(engine, tenant_id),
                ),
                clock,
            ),
            calls=ThreadPoolConcurrentCallsAdapter(),
            context=ComposeCycleContextUseCase(ComposeAgentContextUseCase(), clock),
            agent=DecideCycleUseCase(
                AskFlowAgentUseCase(
                    ComposeAgentContextUseCase(),
                    AskAgentUseCase(
                        catalog,
                        SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id),
                        provider_key_opener,
                        model_call,
                    ),
                )
            ),
            risk=ReviewCycleRiskUseCase(CheckRiskUseCase(markets)),
            orders=SendCycleOrdersUseCase(
                ExecuteCycleOrdersUseCase(
                    ExecuteFlowOrdersUseCase(access, order_exchanges, orders, slippage), follow_flow_orders
                )
            ),
            end=EndCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            journal=JsonCycleJournalAdapter(environment),
        )
        cycles = SqlAlchemyCycleRepositoryAdapter(engine, tenant_id)
        guards = CycleGuards(
            cycles=cycles,
            lock=lock,
            pause=PauseAffectedFlowsUseCase(
                flows, SqlAlchemyAutomaticPauseAdapter(engine, tenant_id), NotifyFlowPausedUseCase(notify)
            ),
            clock=clock,
            failures=NotifyCycleFailureUseCase(flows, NotifyCycleFailedUseCase(notify)),
        )
        checkpoints = SqlAlchemyCycleCheckpointsAdapter(engine, tenant_id)
        return RunCycleUseCase(CycleGraph(steps, cycles, checkpoints), guards)

    return cycle_for


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
    _, catalog = litellm_adapters(source)
    for_tenant = tenant_use_cases(
        engine,
        libsodium_sealing_adapters(source),
        source.environment(),
        worker_adapters(source),
        (catalog, catalog),
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
    models = litellm_adapters(source)
    cycle_for = cycle_of(engine, (opener, provider_key_opener), (environment, slippage), messenger, models)
    cycles = worker_cycles(engine, cycle_for, environment)
    return worker_api_adapters(source, for_tenant, bot, cycles, start_link)


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


type SourcesData = tuple[SourceData, ...]


type WorkerCycle = RunCycleUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, object]


def worker_cycles(
    engine: SqlAlchemyEngine, cycle_for: Callable[[TenantId], WorkerCycle], environment: str
) -> CyclePolling:
    """Each round runs the cycles due and records the actual price beside every expired forecast (R1.3.5)."""
    *_, prices, _ = hyperliquid_adapters(ExchangeNetwork.of_installation(environment))
    clock = system_clock_adapters()
    planned = ThreadsPlannedFlowsAdapter()
    run_due = RunDueCyclesUseCase(
        SqlAlchemyScheduledFlowsAdapter(engine), planned, cycle_for, ThreadCycleLauncherAdapter(), clock
    )
    record_actual_prices = RecordActualPricesOfTenantsUseCase(
        prices, planned.tenants, partial(SqlAlchemyForecastRepositoryAdapter, engine)
    )

    def plan_round() -> None:
        run_due.execute()
        record_actual_prices.execute(RecordActualPricesCommand(clock.now()))

    return CyclePolling(plan_round)
