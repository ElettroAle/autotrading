from collections.abc import Callable, Mapping
from functools import partial

from autotrading.adapters.configuration.source import PROCESS_ENVIRONMENT, ConfigurationSource
from autotrading.adapters.inbound.api.app import ApiApplication
from autotrading.adapters.inbound.api.composition import api_adapters, worker_api_adapters
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import (
    BotPolling,
    CyclePolling,
    OutboxProcessing,
    WorkerAnswers,
    WorkerLoops,
    WorkerUseCases,
    bot_polling,
)
from autotrading.adapters.outbound.alternative_me.composition import alternative_me_adapters
from autotrading.adapters.outbound.apscheduler.composition import apscheduler_adapters
from autotrading.adapters.outbound.coinmarketcap.composition import coinmarketcap_adapters
from autotrading.adapters.outbound.forecaster.composition import forecaster_adapters
from autotrading.adapters.outbound.hyperliquid.composition import (
    HyperliquidAdaptersOfInstallation,
    hyperliquid_adapters,
    hyperliquid_slippage_adapters,
)
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
from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.adapters.outbound.openrouter.model_catalog import OpenRouterModelCatalogAdapter
from autotrading.adapters.outbound.rss.composition import rss_adapters
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.automatic_pause import SqlAlchemyAutomaticPauseAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.composition import SqlAlchemyEngine, sqlalchemy_adapters
from autotrading.adapters.outbound.sqlalchemy.cycle_checkpoints import SqlAlchemyCycleCheckpointsAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.equity_snapshot_repository import (
    SqlAlchemyEquitySnapshotRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.exit_plan_repository import SqlAlchemyExitPlanRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_history import SqlAlchemyFlowHistoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_openings import SqlAlchemyFlowOpeningsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_operations import SqlAlchemyFlowOperationsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_protection_levels import SqlAlchemyFlowProtectionLevelsAdapter
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
from autotrading.adapters.outbound.sqlalchemy.outbox import SqlAlchemyOutboxAdapter
from autotrading.adapters.outbound.sqlalchemy.platform_orders import SqlAlchemyPlatformOrdersAdapter
from autotrading.adapters.outbound.sqlalchemy.protection_repository import SqlAlchemyProtectionRepositoryAdapter
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
from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.adapters.outbound.worker.composition import (
    WorkerAdaptersOfTenant,
    worker_adapters,
    worker_model_catalog_adapters,
)
from autotrading.adapters.outbound.worker.model_catalog import WorkerModelCatalogAdapter
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.agent.ask_agent import AskAgentUseCase
from autotrading.application.agent.ask_flow_agent import AskFlowAgentUseCase
from autotrading.application.agent.compose_agent_context import ComposeAgentContextUseCase
from autotrading.application.agent.list_agent_actions import ListAgentActionsUseCase
from autotrading.application.agent.model_gateways import ModelCatalogs, ModelGateways
from autotrading.application.agent.read_model_catalog import ReadModelCatalogUseCase
from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.close_flow_positions import ClosingPorts
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
from autotrading.application.flows.plan_flow_cycles import PlanFlowCyclesUseCase
from autotrading.application.flows.ports import (
    AccountRemovalPorts,
    CycleContext,
    CycleDecisions,
    FlowAccountPorts,
    FlowModelsPort,
    ReconciliationAlarmPorts,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_account_transfers import ReadAccountTransfersUseCase
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateUseCase
from autotrading.application.flows.read_cycle_source import ReadCycleSourceUseCase
from autotrading.application.flows.read_flow_activity import ReadFlowActivityUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import (
    ReconcileAccountUseCase,
)
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_cycle_equity import RecordCycleEquityUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_manual_closing import RecordManualClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.record_protection_closing import RecordProtectionClosingUseCase
from autotrading.application.flows.review_cycle_risk import ReviewCycleRiskUseCase
from autotrading.application.flows.run_cycle import CycleGuards, RunCycleUseCase
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.application.flows.start_cycle_flow import StartCycleFlowUseCase
from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_reconciliation_alarm import NotifyReconciliationAlarmUseCase
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
    OutboxPort,
)
from autotrading.application.notifications.process_outbox import ProcessOutboxUseCase
from autotrading.application.notifications.send_test_notification import SendTestNotificationUseCase
from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.close_flow_position import CloseFlowPositionUseCase
from autotrading.application.orders.close_verification_position import CloseVerificationPositionUseCase
from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase, FlowOrderProtection
from autotrading.application.orders.follow_flow_orders import (
    FlowOrderFollowers,
    FollowFlowOrdersUseCase,
)
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.open_verification_position import OpenVerificationPositionUseCase
from autotrading.application.orders.order_failures import FailureNames
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionUseCase
from autotrading.application.orders.protect_open_positions import ProtectOpenPositionsUseCase
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.orders.read_minimum_value import ReadMinimumValueUseCase
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.application.sources.collect_cycle_source import CollectCycleSourceUseCase, SourceSystems
from autotrading.application.sources.ports import (
    PriceForecasterPort,
    SentimentPort,
)
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
    installation: tuple[str, HyperliquidAdaptersOfInstallation],
    worker_of: Callable[[TenantId], WorkerAdaptersOfTenant],
    models: tuple[ModelCatalogs, Mapping[str, FlowModelsPort]],
) -> Callable[[TenantId], TenantUseCases]:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""
    model_catalogs, flow_models = models
    credential_sealer, provider_key_sealer = sealers
    environment, hyperliquid = installation
    exchanges, markets, *_ = hyperliquid

    def for_tenant(tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        sealer = credential_sealer(tenant_id)
        bot_identity, account_state, account_activity, position_closing, verification, notifier, ledger_recording = (
            worker_of(tenant_id)
        )
        flow_ledger = SqlAlchemyFlowLedgerAdapter(engine, tenant_id)
        provider_keys = SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id)
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        flow_positions = CloseFlowPositionUseCase(position_closing)
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        closing_notice = NotifyPositionClosedUseCase(
            notifier,
            HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        flow_openings = SqlAlchemyFlowOpeningsAdapter(engine, tenant_id)
        exit_plans = SqlAlchemyExitPlanRepositoryAdapter(engine, tenant_id)
        closing_ports = ClosingPorts(
            SqlAlchemyRunningCycleAdapter(engine),
            flow_positions,
            flow_openings,
            closed_positions,
            closing_notice,
            exit_plans,
        )
        history = SqlAlchemyFlowHistoryAdapter(engine, tenant_id)
        ports = TenantPorts(
            accounts=accounts,
            allocated_capital=flows,
            sealer=sealer,
            exchanges=exchanges,
            account_state=account_state,
            position_closing=position_closing,
            manual_closings=RecordManualClosingUseCase(
                flows, flow_openings, closed_positions, closing_notice, exit_plans
            ),
            verification=verification,
            source_catalog=SOURCE_CATALOG,
            provider_keys=provider_keys,
            provider_key_sealer=provider_key_sealer(tenant_id),
            provider_key_usage=flows,
            model_catalogs=model_catalogs,
            flows=flows,
            running_verifications=SqlAlchemyRunningVerificationsAdapter(engine),
            flow_checks=FlowChecks(
                accounts=FlowAccountPorts(accounts, account_activity, flow_ledger),
                markets=markets,
                models=SelectModelUseCase(flow_models, provider_keys),
                sources=SelectSourceUseCase(SOURCE_CATALOG),
            ),
            flow_positions=flow_positions,
            closing_ports=closing_ports,
            account_removal=AccountRemovalPorts(account_state, accounts),
            account_activity=account_activity,
            account_transfers=account_activity,
            flow_ledger=flow_ledger,
            ledger_recording=ledger_recording,
            flow_operations=SqlAlchemyFlowOperationsAdapter(engine, tenant_id),
            link_codes=SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
            bot_identity=bot_identity,
            linked_chats=SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
            notifier=notifier,
            clock=system_clock_adapters().now,
            closed_positions=closed_positions,
            exit_plans=exit_plans,
            cycle_history=SqlAlchemyCycleRepositoryAdapter(engine, tenant_id),
            flow_directory=flows,
            flow_summaries=ListFlowSummariesUseCase(flows, accounts, SqlAlchemyFlowTimingAdapter(engine, tenant_id)),
            equity_snapshots=SqlAlchemyEquitySnapshotRepositoryAdapter(engine, tenant_id),
            flow_forecasts=SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
            historical_cycles=history,
            historical_closed_positions=history,
            historical_orders=history,
            reconciliation=SqlAlchemyReconciliationRepositoryAdapter(engine, tenant_id),
            account_thresholds=accounts,
            account_names=accounts,
            environment=environment,
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        return TenantUseCases.on(tenant_id, ports)

    return for_tenant


def worker_use_cases(
    engine: SqlAlchemyEngine,
    opener: SodiumCredentialOpenerAdapter,
    installation: tuple[str, HyperliquidAdaptersOfInstallation],
    slippage: Slippage,
    outbox: OutboxPort,
) -> Callable[[TenantId], WorkerUseCases]:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names."""
    environment, hyperliquid = installation
    exchanges, _, order_exchanges, activity_readers, executions_readers, protection_exchanges, *_ = hyperliquid

    verification_failures = FailureNames(VerificationAccountNotFoundError, VerificationStepError)

    def for_tenant(tenant_id: TenantId) -> WorkerUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, exchanges)
        protections = SqlAlchemyProtectionRepositoryAdapter(engine, tenant_id)
        cancel_protections = CancelProtectionsUseCase(access, protection_exchanges, protections)
        close_exchange_position = CloseExchangePositionUseCase(
            access, order_exchanges, orders, slippage, cancel_protections
        )
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
            notify=notify_for(engine, outbox, tenant_id),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, activity_readers),
            read_account_transfers=ReadAccountTransfersUseCase(accounts, opener, activity_readers),
            record_account_executions=RecordAccountExecutionsUseCase(
                SqlAlchemyFlowRepositoryAdapter(engine, tenant_id),
                ReadAccountExecutionsUseCase(accounts, opener, executions_readers),
                SqlAlchemyPlatformOrdersAdapter(engine, tenant_id),
                SqlAlchemyFlowLedgerAdapter(engine, tenant_id),
            ),
        )

    return for_tenant


def cycle_of(
    engine: SqlAlchemyEngine,
    openers: tuple[SodiumCredentialOpenerAdapter, SodiumProviderKeyOpenerAdapter],
    trading: tuple[str, Slippage, HyperliquidAdaptersOfInstallation],
    outbox: OutboxPort,
    predictors: tuple[ModelGateways, PriceForecasterPort],
) -> Callable[[TenantId], WorkerCycle]:
    """Builds, for each cycle, its graph on the adapters bound to the tenant of its flow (ADR 0042, ADR 0104).

    The clock, the models, the sources and the exchanges are the same for every tenant.
    """
    environment, slippage, hyperliquid = trading
    models, forecaster = predictors
    opener, provider_key_opener = openers
    exchanges, markets, order_exchanges, activity_readers, executions_readers, protection_exchanges, *_ = hyperliquid
    *_, prices, market = hyperliquid
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
        exit_plans = SqlAlchemyExitPlanRepositoryAdapter(engine, tenant_id)
        notify = notify_for(engine, outbox, tenant_id)
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        closing_notice = NotifyPositionClosedUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
        activity = ReadAccountActivityUseCase(accounts, opener, activity_readers)
        ledger = SqlAlchemyFlowLedgerAdapter(engine, tenant_id)
        protections = SqlAlchemyProtectionRepositoryAdapter(engine, tenant_id)
        cancel_protections = CancelProtectionsUseCase(access, protection_exchanges, protections)
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            ReadAccountExecutionsUseCase(accounts, opener, executions_readers),
            SqlAlchemyPlatformOrdersAdapter(engine, tenant_id),
            ledger,
        )
        readings = SqlAlchemyReconciliationRepositoryAdapter(engine, tenant_id)
        reconcile_account = ReconcileAccountUseCase(
            flows,
            activity,
            readings,
            RecordOutsideClosingUseCase(
                flows, openings, closed_positions, closing_notice, exit_plans, cancel_protections
            ),
            record_executions,
            RecordProtectionClosingUseCase(
                flows, openings, closed_positions, closing_notice, exit_plans, cancel_protections
            ),
            ReconciliationAlarmPorts(
                accounts, accounts, NotifyReconciliationAlarmUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY)
            ),
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
            ReadCycleFlowStateUseCase(ReadFlowStateUseCase(flows, activity, ledger, exit_plans), reconcile_for_cycle),
            readings,
        )
        follow_flow_orders = FollowFlowOrdersUseCase(
            FlowOrderFollowers(
                NotifyOrderRejectedUseCase(notify),
                NotifyPositionOpenedUseCase(notify, HYPERLIQUID_SETTLEMENT_CURRENCY),
                RecordFlowClosingUseCase(flows, openings, closed_positions, closing_notice, exit_plans),
            )
        )
        steps = CycleSteps(
            start=StartCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            sources=ReadCycleSourceUseCase(
                CollectCycleSourceUseCase(
                    SOURCE_CATALOG,
                    SourceSystems(sentiments, news, prices, forecaster, market),
                    SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
                    SqlAlchemySampleRepositoryAdapter(engine, tenant_id),
                ),
                clock,
            ),
            calls=ThreadPoolConcurrentCallsAdapter(),
            context=ComposeCycleContextUseCase(ComposeAgentContextUseCase(), ListAgentActionsUseCase(), clock),
            agent=DecideCycleUseCase(
                AskFlowAgentUseCase(
                    ComposeAgentContextUseCase(),
                    AskAgentUseCase(
                        models, SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id), provider_key_opener
                    ),
                )
            ),
            risk=ReviewCycleRiskUseCase(CheckRiskUseCase(markets)),
            orders=SendCycleOrdersUseCase(
                ExecuteCycleOrdersUseCase(
                    ExecuteFlowOrdersUseCase(
                        access,
                        order_exchanges,
                        orders,
                        slippage,
                        FlowOrderProtection(
                            ProtectFlowPositionUseCase(
                                order_exchanges, protection_exchanges, protections, orders, slippage
                            ),
                            cancel_protections,
                            UpdateFlowProtectionUseCase(order_exchanges, protection_exchanges, protections),
                        ),
                    ),
                    follow_flow_orders,
                    ProtectOpenPositionsUseCase(access, order_exchanges, protection_exchanges, protections),
                ),
                openings,
                exit_plans,
                flows,
                SqlAlchemyFlowProtectionLevelsAdapter(engine, tenant_id),
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
            activity=ReadFlowActivityUseCase(flows),
        )
        checkpoints = SqlAlchemyCycleCheckpointsAdapter(engine, tenant_id)
        equity = RecordCycleEquityUseCase(SqlAlchemyEquitySnapshotRepositoryAdapter(engine, tenant_id))
        return RunCycleUseCase(CycleGraph(steps, cycles, checkpoints), guards, equity)

    return cycle_for


def notify_for(engine: SqlAlchemyEngine, outbox: OutboxPort, tenant_id: TenantId) -> NotifyUseCase:
    return NotifyUseCase(SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id), outbox)


def link_stores_for(engine: SqlAlchemyEngine, tenant_id: TenantId) -> LinkStores:
    return LinkStores(
        SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
        SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
    )


def create_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> ApiApplication:
    source = ConfigurationSource(configuration)
    engine = sqlalchemy_adapters(source)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    # The API never loads the LiteLLM library: it asks the worker for its catalog (ADR 0148, ADR 0149).
    catalogs: dict[str, WorkerModelCatalogAdapter | OpenRouterModelCatalogAdapter] = {
        **worker_model_catalog_adapters(source),
        **{name: gateway.model_catalog() for name, gateway in openrouter_adapters().items()},
    }
    for_tenant = tenant_use_cases(
        engine,
        libsodium_sealing_adapters(source),
        (source.environment(), hyperliquid_adapters()),
        worker_adapters(source),
        (catalogs, catalogs),
    )
    return api_adapters(source, resolve_tenant, for_tenant, oidc_adapters(source))


def create_worker_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> ApiApplication:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    source = ConfigurationSource(configuration)
    environment = source.environment()
    opener, provider_key_opener = libsodium_opening_adapters(source)
    slippage = hyperliquid_slippage_adapters(source)
    hyperliquid = hyperliquid_adapters()
    engine = sqlalchemy_adapters(source)
    messenger, inbox, start_link = telegram_adapters(source)
    outbox = SqlAlchemyOutboxAdapter(engine)
    for_tenant = worker_use_cases(engine, opener, (environment, hyperliquid), slippage, outbox)
    bot = bot_polling(inbox, lambda bot_inbox: telegram_bot(engine, bot_inbox, messenger, outbox))
    library_gateways = litellm_adapters()
    models: ModelGateways = {**library_gateways, **openrouter_adapters()}
    predictors = (models, forecaster_adapters(source))
    cycle_for = cycle_of(
        engine, (opener, provider_key_opener), (environment, slippage, hyperliquid), outbox, predictors
    )
    cycles = worker_cycles(engine, cycle_for, hyperliquid)
    library_catalog = ReadModelCatalogUseCase(
        {name: gateway.model_catalog() for name, gateway in library_gateways.items()}
    )
    delivery = OutboxProcessing(ProcessOutboxUseCase(outbox, DeliverOutboxMessageUseCase(messenger)).execute)
    loops = WorkerLoops(bot, cycles, delivery)
    return worker_api_adapters(source, for_tenant, loops, WorkerAnswers(start_link, library_catalog))


def telegram_bot(
    engine: SqlAlchemyEngine, inbox: BotInboxPort, messenger: MessengerPort, outbox: OutboxPort
) -> BotPolling:
    """The only bot of the platform, in long polling inside the worker: no inbound port (ADR 0035).

    It answers a message in its chat at once; a test notification goes through the outbox like the real ones.
    """
    link_chat = LinkChatUseCase(
        SqlAlchemyLinkCodeLookupAdapter(engine),
        partial(link_stores_for, engine),
        messenger,
        system_clock_adapters().now,
    )
    test_notification = SendTestNotificationUseCase(
        SqlAlchemyLinkedChatLookupAdapter(engine), partial(notify_for, engine, outbox), messenger
    )
    return BotPolling(AnswerBotMessagesUseCase(inbox, link_chat, test_notification).execute)


type SourcesData = tuple[SourceData, ...]


type WorkerCycle = RunCycleUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, object]


def worker_cycles(
    engine: SqlAlchemyEngine,
    cycle_for: Callable[[TenantId], WorkerCycle],
    hyperliquid: HyperliquidAdaptersOfInstallation,
) -> CyclePolling:
    """Each round plans the cycles of the flows and records the actual price beside every expired forecast (R1.3.5)."""
    *_, prices, _ = hyperliquid
    clock = system_clock_adapters()
    planned = ThreadsPlannedFlowsAdapter()
    plan = PlanFlowCyclesUseCase(
        SqlAlchemyScheduledFlowsAdapter(engine), planned, cycle_for, apscheduler_adapters(), clock
    )
    record_actual_prices = RecordActualPricesOfTenantsUseCase(
        prices, planned.tenants, partial(SqlAlchemyForecastRepositoryAdapter, engine)
    )

    def plan_round() -> None:
        plan.execute()
        record_actual_prices.execute(RecordActualPricesCommand(clock.now()))

    return CyclePolling(plan_round)
