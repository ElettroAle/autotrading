from collections.abc import Callable, Mapping
from functools import partial

from autotrading.adapters.configuration.source import PROCESS_ENVIRONMENT, ConfigurationSource
from autotrading.adapters.inbound.api.app import ApiApplication
from autotrading.adapters.inbound.api.composition import api_adapters, worker_api_adapters
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import (
    BotPolling,
    CyclePolling,
    DailyChecks,
    OutboxProcessing,
    WorkerAnswers,
    WorkerLoops,
    WorkerUseCases,
    bot_polling,
)
from autotrading.adapters.inbound.mcp.composition import mcp_adapters
from autotrading.adapters.inbound.mcp.server import McpApplication
from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from autotrading.adapters.outbound.alternative_me.composition import alternative_me_adapters
from autotrading.adapters.outbound.apscheduler.composition import apscheduler_adapters, apscheduler_daily_check_adapters
from autotrading.adapters.outbound.arkham.composition import arkham_adapters
from autotrading.adapters.outbound.binance.composition import binance_adapters
from autotrading.adapters.outbound.coinmarketcap.composition import coinmarketcap_adapters
from autotrading.adapters.outbound.dashboard.composition import dashboard_adapters
from autotrading.adapters.outbound.forecaster.composition import forecaster_adapters
from autotrading.adapters.outbound.grafana_cloud.composition import grafana_cloud_telemetry_adapters
from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.hyperliquid.composition import (
    HyperliquidAdaptersOfInstallation,
    hyperliquid_adapters,
    hyperliquid_slippage_adapters,
)
from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.executions import HyperliquidAccountExecutionsAdapter
from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.adapters.outbound.json.cycle_journal import JsonCycleJournalAdapter
from autotrading.adapters.outbound.libsodium.composition import (
    SealersOfTenant,
    libsodium_opening_adapters,
    libsodium_sealing_adapters,
)
from autotrading.adapters.outbound.libsodium.mail_password_opener import SodiumMailPasswordOpenerAdapter
from autotrading.adapters.outbound.libsodium.opener import (
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.source_secrets_opener import SodiumSourceSecretsOpenerAdapter
from autotrading.adapters.outbound.litellm.composition import litellm_adapters
from autotrading.adapters.outbound.lunarcrush.composition import lunarcrush_adapters
from autotrading.adapters.outbound.oidc.composition import oidc_adapters
from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.adapters.outbound.openrouter.model_catalog import OpenRouterModelCatalogAdapter
from autotrading.adapters.outbound.process_memory.composition import (
    RememberedAccountActivity,
    process_memory_adapters,
    process_memory_cycle_notices_adapters,
)
from autotrading.adapters.outbound.process_memory.cycle_notices import (
    ProcessMemoryOpeningBlockedNoticeAdapter,
    ProcessMemoryOpeningReducedNoticeAdapter,
    ProcessMemoryOpeningsSuspendedNoticeAdapter,
    ProcessMemoryOrderRejectedNoticeAdapter,
    ProcessMemoryPositionClosedNoticeAdapter,
    ProcessMemoryPositionOpenedNoticeAdapter,
)
from autotrading.adapters.outbound.rss.composition import rss_adapters
from autotrading.adapters.outbound.smtp.composition import smtp_adapters
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.alert_repository import SqlAlchemyAlertRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.automatic_pause import SqlAlchemyAutomaticPauseAdapter
from autotrading.adapters.outbound.sqlalchemy.channel_preferences_repository import (
    SqlAlchemyChannelPreferencesRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.composition import (
    SimulatedExchangeOfTenant,
    SqlAlchemyEngine,
    sqlalchemy_adapters,
    sqlalchemy_simulated_exchange_adapters,
    sqlalchemy_simulation_adapters,
)
from autotrading.adapters.outbound.sqlalchemy.cycle_checkpoints import SqlAlchemyCycleCheckpointsAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.emergency_closing_log import SqlAlchemyEmergencyClosingLogAdapter
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
from autotrading.adapters.outbound.sqlalchemy.flow_status import SqlAlchemyFlowStatusAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_timing import SqlAlchemyFlowTimingAdapter
from autotrading.adapters.outbound.sqlalchemy.forecast_repository import SqlAlchemyForecastRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.key_expiries import (
    SqlAlchemyKeyExpiriesAdapter,
    SqlAlchemyKeyExpiryNoticeRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.link_code_repository import (
    SqlAlchemyLinkCodeLookupAdapter,
    SqlAlchemyLinkCodeRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import (
    SqlAlchemyLinkedChatLookupAdapter,
    SqlAlchemyLinkedChatRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.mail_server_repository import SqlAlchemyMailServerRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.notification_email_repository import (
    SqlAlchemyNotificationEmailRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.notification_inbox import SqlAlchemyNotificationInboxAdapter
from autotrading.adapters.outbound.sqlalchemy.notified_flows import SqlAlchemyNotifiedFlowsAdapter
from autotrading.adapters.outbound.sqlalchemy.openings_suspension import SqlAlchemyOpeningsSuspensionAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.outbox import SqlAlchemyOutboxAdapter
from autotrading.adapters.outbound.sqlalchemy.past_decisions import SqlAlchemyPastDecisionsAdapter
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
from autotrading.adapters.outbound.sqlalchemy.simulated_exchange import SqlAlchemySimulatedExchangeAdapter
from autotrading.adapters.outbound.sqlalchemy.source_credentials_repository import (
    SqlAlchemySourceCredentialsRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.verification_locks import SqlAlchemyRunningVerificationsAdapter
from autotrading.adapters.outbound.sqlalchemy.verification_run_repository import (
    SqlAlchemyVerificationRunRepositoryAdapter,
)
from autotrading.adapters.outbound.system_clock.composition import system_clock_adapters, system_clock_pause_adapters
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
from autotrading.application.flows.guard_flow_loss import GuardFlowLossUseCase
from autotrading.application.flows.list_flow_summaries import ListFlowSummariesUseCase
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.application.flows.notify_unattributable import (
    NotifyUnattributableUseCase,
    UnattributableNotices,
)
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.pause_after_consecutive_failures import PauseAfterConsecutiveFailuresUseCase
from autotrading.application.flows.pause_flows_on_expired_keys import (
    PauseFlowsOnExpiredKeysCommand,
    PauseFlowsOnExpiredKeysUseCase,
)
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
from autotrading.application.flows.read_cycle_flow import CycleAccountReadings, ReadCycleFlowUseCase
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
from autotrading.application.flows.reverse_cycle_positions import ReverseCyclePositionsUseCase
from autotrading.application.flows.review_cycle_risk import ReviewCycleRiskUseCase
from autotrading.application.flows.run_cycle import CycleGuards, RunCycleUseCase
from autotrading.application.flows.run_cycle_on_demand import RunCycleOnDemandUseCase
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.application.flows.start_cycle_flow import StartCycleFlowUseCase
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.check_key_expiries import CheckKeyExpiriesUseCase
from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_opening_blocked import NotifyOpeningBlockedUseCase
from autotrading.application.notifications.notify_opening_reduced import NotifyOpeningReducedUseCase
from autotrading.application.notifications.notify_openings_suspended import NotifyOpeningsSuspendedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_reconciliation_alarm import NotifyReconciliationAlarmUseCase
from autotrading.application.notifications.notify_source_credentials_rejected import (
    NotifySourceCredentialsRejectedUseCase,
)
from autotrading.application.notifications.notify_unattributable_fill import NotifyUnattributableFillUseCase
from autotrading.application.notifications.notify_unattributable_position import (
    NotifyUnattributablePositionUseCase,
)
from autotrading.application.notifications.ports import (
    BotInboxPort,
    LinkStores,
    MailerPort,
    MailServerAccess,
    MessengerPort,
    NotificationInbox,
    NotificationLinkPort,
    NotificationRoutes,
    OutboxPort,
)
from autotrading.application.notifications.process_outbox import ProcessOutboxUseCase
from autotrading.application.notifications.schedule_key_expiry_checks import ScheduleKeyExpiryChecksUseCase
from autotrading.application.notifications.send_test_email import SendTestEmailUseCase
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
from autotrading.application.orders.ports import ExchangeConnection
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionUseCase
from autotrading.application.orders.protect_open_positions import ProtectOpenPositionsUseCase
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.orders.read_minimum_value import ReadMinimumValueUseCase
from autotrading.application.orders.record_waiting_protections import RecordWaitingProtectionsUseCase
from autotrading.application.orders.settle_simulated_positions import (
    SettleSimulatedPositionsCommand,
    SettleSimulatedPositionsUseCase,
)
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.application.sources.aggregate_cycle_sources import AggregateCycleSourcesUseCase
from autotrading.application.sources.collect_cycle_source import CollectCycleSourceUseCase, SourceCredentialServices
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.application.sources.ports import (
    PriceForecasterPort,
)
from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand
from autotrading.application.sources.record_actual_prices_of_tenants import RecordActualPricesOfTenantsUseCase
from autotrading.application.sources.try_source_adapter import TrialServices, TrySourceAdapterUseCase
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.ports import ProcedureOrders
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_interval import DEFAULT_CYCLE_INTERVAL
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId


def tenant_use_cases(
    engine: SqlAlchemyEngine,
    sealers: SealersOfTenant,
    installation: tuple[str, HyperliquidAdaptersOfInstallation, SourceSystems, SimulatedExecution],
    worker: tuple[Callable[[TenantId], WorkerAdaptersOfTenant], RememberedAccountActivity],
    models: tuple[ModelCatalogs, Mapping[str, FlowModelsPort]],
) -> Callable[[TenantId], TenantUseCases]:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them.

    The readings of the accounts go through the memory of the process: in the API they serve only the dashboard (Bug
    635, ADR cache-delle-letture-del-conto-come-decorator-in-memoria).
    """
    worker_of, remembered_activity = worker
    model_catalogs, flow_models = models
    credential_sealer, provider_key_sealer, mail_password_sealer, source_secrets_sealer = sealers
    environment, hyperliquid, systems, simulation = installation
    sources = ListSourcesUseCase(systems)

    def for_tenant(tenant_id: TenantId) -> TenantUseCases:
        exchanges, markets, *_, simulated = exchanges_of_tenant(engine, simulation, hyperliquid, tenant_id)
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        sealer = credential_sealer(tenant_id)
        (
            bot_identity,
            account_state,
            worker_account_activity,
            position_closing,
            verification,
            notifier,
            ledger_recording,
            on_demand_cycles,
            email_tests,
            source_trials,
        ) = worker_of(tenant_id)
        account_activity = remembered_activity(worker_account_activity, tenant_id)
        flow_ledger = SqlAlchemyFlowLedgerAdapter(engine, tenant_id)
        provider_keys = SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id)
        source_credentials = SqlAlchemySourceCredentialsRepositoryAdapter(engine, tenant_id)
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        flow_positions = CloseFlowPositionUseCase(position_closing)
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        flow_status = SqlAlchemyFlowStatusAdapter(engine, tenant_id, HYPERLIQUID_SETTLEMENT_CURRENCY)
        closing_notice = NotifyPositionClosedUseCase(
            NotifyFlowEventUseCase(notifier, flow_status),
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
        cycle_history = SqlAlchemyCycleRepositoryAdapter(engine, tenant_id)
        alerts = SqlAlchemyAlertRepositoryAdapter(engine, tenant_id)
        ports = TenantPorts(
            accounts=accounts,
            allocated_capital=flows,
            sealer=sealer,
            exchanges=exchanges,
            virtual_balances=simulated,
            account_state=account_state,
            position_closing=position_closing,
            manual_closings=RecordManualClosingUseCase(
                flows, flow_openings, closed_positions, closing_notice, exit_plans
            ),
            verification=verification,
            sources=sources,
            source_credentials=source_credentials,
            source_secrets_sealer=source_secrets_sealer(tenant_id),
            source_trials=source_trials,
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
                sources=SelectSourceUseCase(sources, source_credentials),
            ),
            flow_positions=flow_positions,
            closing_ports=closing_ports,
            account_removal=AccountRemovalPorts(account_state, accounts),
            account_activity=account_activity,
            account_transfers=worker_account_activity,
            flow_ledger=flow_ledger,
            ledger_recording=ledger_recording,
            on_demand_cycles=on_demand_cycles,
            flow_operations=SqlAlchemyFlowOperationsAdapter(engine, tenant_id),
            link_codes=SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
            bot_identity=bot_identity,
            linked_chats=SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
            notifier=notifier,
            flow_status=flow_status,
            notification_emails=SqlAlchemyNotificationEmailRepositoryAdapter(engine, tenant_id),
            mail_servers=SqlAlchemyMailServerRepositoryAdapter(engine, tenant_id),
            mail_password_sealer=mail_password_sealer(tenant_id),
            email_tests=email_tests,
            channel_preferences=SqlAlchemyChannelPreferencesRepositoryAdapter(engine, tenant_id),
            notified_flows=SqlAlchemyNotifiedFlowsAdapter(engine, tenant_id),
            clock=system_clock_adapters().now,
            closed_positions=closed_positions,
            exit_plans=exit_plans,
            protection_levels=SqlAlchemyFlowProtectionLevelsAdapter(engine, tenant_id),
            cycle_history=cycle_history,
            decision_history=cycle_history,
            flow_directory=flows,
            flow_summaries=ListFlowSummariesUseCase(flows, accounts, SqlAlchemyFlowTimingAdapter(engine, tenant_id)),
            flow_timing=SqlAlchemyFlowTimingAdapter(engine, tenant_id),
            past_decisions=SqlAlchemyPastDecisionsAdapter(engine, tenant_id),
            equity_snapshots=SqlAlchemyEquitySnapshotRepositoryAdapter(engine, tenant_id),
            openings_suspensions=SqlAlchemyOpeningsSuspensionAdapter(engine, tenant_id),
            flow_forecasts=SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
            historical_cycles=history,
            historical_closed_positions=history,
            historical_orders=history,
            reconciliation=SqlAlchemyReconciliationRepositoryAdapter(engine, tenant_id),
            account_thresholds=accounts,
            account_names=accounts,
            automatic_pause=SqlAlchemyAutomaticPauseAdapter(engine, tenant_id),
            emergency_closings=SqlAlchemyEmergencyClosingLogAdapter(engine, tenant_id),
            alerts=alerts,
            alert_resolution=alerts,
            notification_inbox=SqlAlchemyNotificationInboxAdapter(engine, tenant_id),
            environment=environment,
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        return TenantUseCases.on(tenant_id, ports)

    return for_tenant


def worker_use_cases(
    engine: SqlAlchemyEngine,
    openers: tuple[SodiumCredentialOpenerAdapter, Callable[[TenantId], SodiumMailPasswordOpenerAdapter]],
    trading: tuple[str, Slippage, HyperliquidAdaptersOfInstallation, SimulatedExecution],
    notifications: tuple[OutboxPort, MailerPort, NotificationLinkPort],
    cycles: tuple[Callable[[TenantId], WorkerCycle], SourceSystems, SodiumSourceSecretsOpenerAdapter],
) -> Callable[[TenantId], WorkerUseCases]:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names.

    The cycle asked for now runs on the graph of the planned cycles, composed only when the request asks for it; the
    trial of a source reads it as a cycle of the interval of a flow that names none (R6.3.1).
    """
    cycle_for, systems, source_secrets_opener = cycles
    environment, slippage, hyperliquid, simulation = trading
    verification_exchanges, *_ = hyperliquid
    opener, mail_password_opener = openers
    outbox, mailer, links = notifications

    verification_failures = FailureNames(VerificationAccountNotFoundError, VerificationStepError)

    def for_tenant(tenant_id: TenantId) -> WorkerUseCases:
        exchanges, _, order_exchanges, activity_readers, executions_readers, _ = exchanges_of_tenant(
            engine, simulation, hyperliquid, tenant_id
        )
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, exchanges)
        protections = SqlAlchemyProtectionRepositoryAdapter(engine, tenant_id)
        cancel_protections = CancelProtectionsUseCase(access, order_exchanges, protections)
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
                    ReadAccountForVerificationUseCase(accounts, opener, verification_exchanges),
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
            notify=notify_for(engine, outbox, links, tenant_id),
            send_test_email=SendTestEmailUseCase(
                SqlAlchemyNotificationEmailRepositoryAdapter(engine, tenant_id),
                mail_server_access_for(engine, mail_password_opener, tenant_id),
                mailer,
            ),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, activity_readers),
            read_account_transfers=ReadAccountTransfersUseCase(accounts, opener, activity_readers),
            record_account_executions=RecordAccountExecutionsUseCase(
                SqlAlchemyFlowRepositoryAdapter(engine, tenant_id),
                ReadAccountExecutionsUseCase(accounts, opener, executions_readers),
                SqlAlchemyPlatformOrdersAdapter(engine, tenant_id),
                SqlAlchemyFlowLedgerAdapter(engine, tenant_id),
            ),
            run_cycle_on_demand=RunCycleOnDemandUseCase(
                SqlAlchemyFlowRepositoryAdapter(engine, tenant_id),
                SqlAlchemyFlowTimingAdapter(engine, tenant_id),
                system_clock_adapters(),
                lambda command: cycle_for(tenant_id).execute(command),
            ),
            try_source_adapter=TrySourceAdapterUseCase(
                systems,
                SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
                OpenSourceCredentialsUseCase(
                    SqlAlchemySourceCredentialsRepositoryAdapter(engine, tenant_id), source_secrets_opener
                ),
                TrialServices(ThreadPoolConcurrentCallsAdapter(), system_clock_adapters(), DEFAULT_CYCLE_INTERVAL),
            ),
        )

    return for_tenant


def cycle_of(
    engine: SqlAlchemyEngine,
    openers: tuple[SodiumCredentialOpenerAdapter, SodiumProviderKeyOpenerAdapter, SodiumSourceSecretsOpenerAdapter],
    trading: tuple[str, Slippage, HyperliquidAdaptersOfInstallation, SimulatedExecution],
    notifications: tuple[OutboxPort, NotificationLinkPort],
    predictors: tuple[ModelGateways, PriceForecasterPort],
) -> Callable[[TenantId], WorkerCycle]:
    """Builds, for each cycle, its graph on the adapters bound to the tenant of its flow (ADR 0042, ADR 0104).

    The clock, the models, the sources and the exchanges are the same for every tenant.
    """
    environment, slippage, hyperliquid, simulation = trading
    models, forecaster = predictors
    opener, provider_key_opener, source_secrets_opener = openers
    clock = system_clock_adapters()
    systems = source_systems(hyperliquid, forecaster)
    lock = SqlAlchemyFlowLockAdapter(engine)

    def cycle_for(tenant_id: TenantId) -> WorkerCycle:
        exchanges, markets, order_exchanges, activity_readers, executions_readers, _ = exchanges_of_tenant(
            engine, simulation, hyperliquid, tenant_id
        )
        accounts = SqlAlchemyAccountRepositoryAdapter(engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(engine, tenant_id)
        access = OpenTradingAccessUseCase(accounts, opener)
        flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
        openings = SqlAlchemyFlowOpeningsAdapter(engine, tenant_id)
        exit_plans = SqlAlchemyExitPlanRepositoryAdapter(engine, tenant_id)
        notify = notify_for(engine, *notifications, tenant_id)
        notify_flow = NotifyFlowEventUseCase(
            notify, SqlAlchemyFlowStatusAdapter(engine, tenant_id, HYPERLIQUID_SETTLEMENT_CURRENCY)
        )
        closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(engine, tenant_id)
        notices = process_memory_cycle_notices_adapters()
        closing_notice = ProcessMemoryPositionClosedNoticeAdapter(
            NotifyPositionClosedUseCase(notify_flow, HYPERLIQUID_SETTLEMENT_CURRENCY), notices
        )
        activity = ReadAccountActivityUseCase(accounts, opener, activity_readers)
        ledger = SqlAlchemyFlowLedgerAdapter(engine, tenant_id)
        protections = SqlAlchemyProtectionRepositoryAdapter(engine, tenant_id)
        protection_levels = SqlAlchemyFlowProtectionLevelsAdapter(engine, tenant_id)
        cancel_protections = CancelProtectionsUseCase(access, order_exchanges, protections)
        record_executions = RecordAccountExecutionsUseCase(
            flows,
            ReadAccountExecutionsUseCase(accounts, opener, executions_readers),
            SqlAlchemyPlatformOrdersAdapter(engine, tenant_id),
            ledger,
        )
        readings = SqlAlchemyReconciliationRepositoryAdapter(engine, tenant_id)
        alerts = SqlAlchemyAlertRepositoryAdapter(engine, tenant_id)
        reconcile_account = ReconcileAccountUseCase(
            flows,
            activity,
            readings,
            RecordOutsideClosingUseCase(
                flows, openings, closed_positions, closing_notice, exit_plans, cancel_protections
            ),
            record_executions,
            ledger,
            RecordProtectionClosingUseCase(
                flows, openings, closed_positions, closing_notice, exit_plans, cancel_protections
            ),
            ReconciliationAlarmPorts(
                accounts, accounts, NotifyReconciliationAlarmUseCase(notify, alerts, HYPERLIQUID_SETTLEMENT_CURRENCY)
            ),
            alerts,
        )
        reconcile_for_cycle = ReconcileAccountForCycleUseCase(
            reconcile_account,
            NotifyUnattributableUseCase(
                accounts,
                UnattributableNotices(
                    NotifyUnattributablePositionUseCase(notify, alerts),
                    NotifyUnattributableFillUseCase(notify, alerts),
                ),
            ),
        )
        read_cycle_flow = ReadCycleFlowUseCase(
            flows,
            SqlAlchemyFlowTimingAdapter(engine, tenant_id),
            CycleAccountReadings(
                ReadCycleAccountUseCase(accounts, accounts, opener, exchanges),
                RecordWaitingProtectionsUseCase(access, order_exchanges, protections),
            ),
            ReadCycleFlowStateUseCase(
                ReadFlowStateUseCase(flows, activity, ledger, exit_plans, protection_levels), reconcile_for_cycle
            ),
            readings,
        )
        follow_flow_orders = FollowFlowOrdersUseCase(
            FlowOrderFollowers(
                ProcessMemoryOrderRejectedNoticeAdapter(NotifyOrderRejectedUseCase(notify_flow), notices),
                ProcessMemoryPositionOpenedNoticeAdapter(
                    NotifyPositionOpenedUseCase(notify_flow, HYPERLIQUID_SETTLEMENT_CURRENCY), notices
                ),
                RecordFlowClosingUseCase(flows, openings, closed_positions, closing_notice, exit_plans),
            )
        )
        check_risk = CheckRiskUseCase(markets)
        loss_guard = GuardFlowLossUseCase(
            SqlAlchemyOpeningsSuspensionAdapter(engine, tenant_id),
            SqlAlchemyEquitySnapshotRepositoryAdapter(engine, tenant_id),
            ProcessMemoryOpeningsSuspendedNoticeAdapter(NotifyOpeningsSuspendedUseCase(notify_flow), notices),
            clock,
        )
        reduced_notice = ProcessMemoryOpeningReducedNoticeAdapter(
            NotifyOpeningReducedUseCase(notify_flow, HYPERLIQUID_SETTLEMENT_CURRENCY), notices
        )
        blocked_notice = ProcessMemoryOpeningBlockedNoticeAdapter(NotifyOpeningBlockedUseCase(notify_flow), notices)
        retry = TransientRetry(system_clock_pause_adapters(), clock)
        send_orders = SendCycleOrdersUseCase(
            ExecuteCycleOrdersUseCase(
                ExecuteFlowOrdersUseCase(
                    access,
                    order_exchanges,
                    orders,
                    slippage,
                    FlowOrderProtection(
                        ProtectFlowPositionUseCase(order_exchanges, protections, orders, slippage),
                        cancel_protections,
                        UpdateFlowProtectionUseCase(order_exchanges, protections),
                    ),
                    retry,
                ),
                follow_flow_orders,
                ProtectOpenPositionsUseCase(access, order_exchanges, protections, retry),
            ),
            openings,
            exit_plans,
            flows,
            protection_levels,
        )
        steps = CycleSteps(
            start=StartCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            sources=ReadCycleSourceUseCase(
                CollectCycleSourceUseCase(
                    systems,
                    SqlAlchemyForecastRepositoryAdapter(engine, tenant_id),
                    SqlAlchemySampleRepositoryAdapter(engine, tenant_id),
                    SourceCredentialServices(
                        SqlAlchemySourceCredentialsRepositoryAdapter(engine, tenant_id),
                        source_secrets_opener,
                        NotifySourceCredentialsRejectedUseCase(notify),
                    ),
                ),
                clock,
            ),
            calls=ThreadPoolConcurrentCallsAdapter(),
            context=ComposeCycleContextUseCase(
                ComposeAgentContextUseCase(),
                ListAgentActionsUseCase(),
                AggregateCycleSourcesUseCase(),
                clock,
                SqlAlchemyPastDecisionsAdapter(engine, tenant_id),
            ),
            agent=DecideCycleUseCase(
                AskFlowAgentUseCase(
                    ComposeAgentContextUseCase(),
                    AskAgentUseCase(
                        models,
                        SqlAlchemyProviderKeyRepositoryAdapter(engine, tenant_id),
                        provider_key_opener,
                        system_clock_pause_adapters(),
                    ),
                )
            ),
            risk=ReviewCycleRiskUseCase(check_risk, loss_guard, reduced_notice, blocked_notice),
            orders=send_orders,
            reversal=ReverseCyclePositionsUseCase(
                record_executions,
                read_cycle_flow,
                check_risk,
                loss_guard,
                reduced_notice,
                blocked_notice,
                send_orders,
                retry,
            ),
            end=EndCycleFlowUseCase(reconcile_for_cycle, read_cycle_flow),
            journal=JsonCycleJournalAdapter(environment),
        )
        cycles = SqlAlchemyCycleRepositoryAdapter(engine, tenant_id)
        pause = PauseAffectedFlowsUseCase(
            flows, SqlAlchemyAutomaticPauseAdapter(engine, tenant_id), NotifyFlowPausedUseCase(notify_flow, alerts)
        )
        guards = CycleGuards(
            cycles=cycles,
            lock=lock,
            pause=pause,
            clock=clock,
            failures=NotifyCycleFailureUseCase(flows, NotifyCycleFailedUseCase(notify_flow)),
            activity=ReadFlowActivityUseCase(flows),
            consecutive_failures=PauseAfterConsecutiveFailuresUseCase(flows, cycles, pause),
            expired_keys=PauseFlowsOnExpiredKeysUseCase(
                SqlAlchemyKeyExpiriesAdapter(engine, tenant_id), flows, pause, clock
            ),
        )
        checkpoints = SqlAlchemyCycleCheckpointsAdapter(engine, tenant_id)
        equity = RecordCycleEquityUseCase(SqlAlchemyEquitySnapshotRepositoryAdapter(engine, tenant_id))
        return RunCycleUseCase(CycleGraph(steps, cycles, checkpoints, retry), guards, equity, notices)

    return cycle_for


def check_key_expiries(
    engine: SqlAlchemyEngine, notifications: tuple[OutboxPort, NotificationLinkPort], tenant_id: TenantId
) -> None:
    """The daily check of one tenant: the notices and alerts of its keys, then the pause of the flows of an expired key
    (R6.2.2, ADR controllo-giornaliero-delle-scadenze)."""
    clock = system_clock_adapters()
    keys = SqlAlchemyKeyExpiriesAdapter(engine, tenant_id)
    alerts = SqlAlchemyAlertRepositoryAdapter(engine, tenant_id)
    notify = notify_for(engine, *notifications, tenant_id)
    notices = SqlAlchemyKeyExpiryNoticeRepositoryAdapter(engine, tenant_id)
    CheckKeyExpiriesUseCase(keys, notices, alerts, notify, clock).execute()
    flows = SqlAlchemyFlowRepositoryAdapter(engine, tenant_id)
    notify_flow = NotifyFlowEventUseCase(
        notify, SqlAlchemyFlowStatusAdapter(engine, tenant_id, HYPERLIQUID_SETTLEMENT_CURRENCY)
    )
    pause = PauseAffectedFlowsUseCase(
        flows, SqlAlchemyAutomaticPauseAdapter(engine, tenant_id), NotifyFlowPausedUseCase(notify_flow, alerts)
    )
    PauseFlowsOnExpiredKeysUseCase(keys, flows, pause, clock).execute(PauseFlowsOnExpiredKeysCommand())


def notify_for(
    engine: SqlAlchemyEngine, outbox: OutboxPort, links: NotificationLinkPort, tenant_id: TenantId
) -> NotifyUseCase:
    return NotifyUseCase(
        SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
        SqlAlchemyNotificationEmailRepositoryAdapter(engine, tenant_id),
        SqlAlchemyMailServerRepositoryAdapter(engine, tenant_id),
        outbox,
        NotificationRoutes(SqlAlchemyChannelPreferencesRepositoryAdapter(engine, tenant_id), links),
        NotificationInbox(SqlAlchemyNotificationInboxAdapter(engine, tenant_id), system_clock_adapters()),
    )


def mail_server_access_for(
    engine: SqlAlchemyEngine,
    opener_of: Callable[[TenantId], SodiumMailPasswordOpenerAdapter],
    tenant_id: TenantId,
) -> MailServerAccess:
    """The mail server of the tenant of an email and the opener of its password, in the worker alone (ADR
    invio-dal-server-di-posta-del-tenant)."""
    return MailServerAccess(SqlAlchemyMailServerRepositoryAdapter(engine, tenant_id), opener_of(tenant_id))


def link_stores_for(engine: SqlAlchemyEngine, tenant_id: TenantId) -> LinkStores:
    return LinkStores(
        SqlAlchemyLinkCodeRepositoryAdapter(engine, tenant_id),
        SqlAlchemyLinkedChatRepositoryAdapter(engine, tenant_id),
    )


def source_systems(hyperliquid: HyperliquidAdaptersOfInstallation, forecaster: PriceForecasterPort) -> SourceSystems:
    """The adapters of the sources, the same in the api and in the worker: their declarations need no secret (R4.1.1,
    ADR fonti-con-adapter-dichiarati)."""
    *_, prices, market = hyperliquid
    return SourceSystems(
        (alternative_me_adapters(), coinmarketcap_adapters()),
        rss_adapters(),
        prices,
        forecaster,
        market,
        (arkham_adapters(),),
        (binance_adapters(),),
        (lunarcrush_adapters(),),
    )


type ExchangesOfTenant = tuple[
    dict[str, HyperliquidExchangeAdapter | SqlAlchemySimulatedExchangeAdapter],
    dict[str, HyperliquidMarketsAdapter],
    dict[str, ExchangeConnection],
    dict[str, HyperliquidAccountActivityAdapter | SqlAlchemySimulatedExchangeAdapter],
    dict[str, HyperliquidAccountExecutionsAdapter | SqlAlchemySimulatedExchangeAdapter],
    SimulatedExchangeOfTenant,
]


def exchanges_of_tenant(
    engine: SqlAlchemyEngine,
    simulation: SimulatedExecution,
    hyperliquid: HyperliquidAdaptersOfInstallation,
    tenant_id: TenantId,
) -> ExchangesOfTenant:
    """The exchanges an account of the tenant can be on, by name (ADR 0152): those of the installation, and the
    simulated exchange, which reads the real market and keeps the accounts of the tenant (R6.3.2, ADR
    exchange-simulato-con-porte-di-lettura-e-scrittura). One name gives every port of its exchange.
    """
    exchanges, markets, order_exchanges, activity_readers, executions_readers, real_market, *_ = hyperliquid
    real_orders, real_markets = real_market
    simulated = sqlalchemy_simulated_exchange_adapters(engine, simulation, tenant_id)
    return (
        {**exchanges, **simulated},
        {**markets, **dict.fromkeys(simulated, real_markets)},
        {
            **order_exchanges,
            **{name: ExchangeConnection(real_orders, adapter, adapter) for name, adapter in simulated.items()},
        },
        {**activity_readers, **simulated},
        {**executions_readers, **simulated},
        simulated,
    )


def create_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> ApiApplication:
    source = ConfigurationSource(configuration)
    grafana_cloud_telemetry_adapters(source, "autotrading-api")
    engine = sqlalchemy_adapters(source)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    for_tenant = api_tenant_use_cases(
        engine,
        libsodium_sealing_adapters(source),
        (source.environment(), forecaster_adapters(source), sqlalchemy_simulation_adapters(source)),
        (worker_adapters(source), process_memory_adapters()),
        worker_model_catalog_adapters(source),
    )
    return api_adapters(source, resolve_tenant, for_tenant, oidc_adapters(source))


def create_mcp_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> McpApplication:
    """The MCP server: the use cases of the API for the tenant of the request, in a container of its own (ADR
    server-mcp-in-un-container-proprio-con-accesso-entra)."""
    source = ConfigurationSource(configuration)
    engine = sqlalchemy_adapters(source)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    for_tenant = api_tenant_use_cases(
        engine,
        libsodium_sealing_adapters(source),
        (source.environment(), forecaster_adapters(source), sqlalchemy_simulation_adapters(source)),
        (worker_adapters(source), process_memory_adapters()),
        worker_model_catalog_adapters(source),
    )
    return mcp_adapters(source, resolve_tenant, mcp_use_cases(for_tenant), oidc_adapters(source))


def api_tenant_use_cases(
    engine: SqlAlchemyEngine,
    sealers: SealersOfTenant,
    installation: tuple[str, PriceForecasterPort, SimulatedExecution],
    worker: tuple[Callable[[TenantId], WorkerAdaptersOfTenant], RememberedAccountActivity],
    worker_catalogs: Mapping[str, WorkerModelCatalogAdapter],
) -> Callable[[TenantId], TenantUseCases]:
    """The use cases of the API for each tenant, with the exchanges and the models of the installation."""
    environment, forecaster, simulation = installation
    # The API never loads the LiteLLM library: it asks the worker for its catalog (ADR 0148, ADR 0149).
    catalogs: dict[str, WorkerModelCatalogAdapter | OpenRouterModelCatalogAdapter] = {
        **worker_catalogs,
        **{name: gateway.model_catalog() for name, gateway in openrouter_adapters().items()},
    }
    hyperliquid = hyperliquid_adapters()
    return tenant_use_cases(
        engine,
        sealers,
        (environment, hyperliquid, source_systems(hyperliquid, forecaster), simulation),
        worker,
        (catalogs, catalogs),
    )


def mcp_use_cases(for_tenant: Callable[[TenantId], TenantUseCases]) -> Callable[[TenantId], McpUseCases]:
    """The use cases of the API the tools of the MCP server call, the same instances for the same tenant."""

    def mcp_for_tenant(tenant_id: TenantId) -> McpUseCases:
        use_cases = for_tenant(tenant_id)
        return McpUseCases(
            list_flow_overviews=use_cases.list_flow_overviews,
            get_flow=use_cases.get_flow,
            read_flow_results=use_cases.read_flow_results,
            list_closed_positions=use_cases.list_closed_positions,
            list_cycles=use_cases.list_cycles,
            read_cycle=use_cases.read_cycle,
            read_flow_memory=use_cases.read_flow_memory,
            read_flow_statistics=use_cases.read_flow_statistics,
            rank_flows=use_cases.rank_flows,
            list_accounts=use_cases.list_accounts,
            create_flow=use_cases.create_flow,
            import_flow_strategy=use_cases.import_flow_strategy,
            duplicate_flow=use_cases.duplicate_flow,
            modify_flow=use_cases.modify_flow,
            change_flow_status=use_cases.change_flow_status,
            stop_flow=use_cases.stop_flow,
            archive_flow=use_cases.archive_flow,
            cash_out_profits=use_cases.cash_out_profits,
            change_allocated_capital=use_cases.change_allocated_capital,
            request_on_demand_cycle=use_cases.request_on_demand_cycle,
            resume_flow_openings=use_cases.resume_flow_openings,
        )

    return mcp_for_tenant


def create_worker_application(configuration: Mapping[str, str] = PROCESS_ENVIRONMENT) -> ApiApplication:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    source = ConfigurationSource(configuration)
    grafana_cloud_telemetry_adapters(source, "autotrading-worker")
    environment = source.environment()
    opener, provider_key_opener, mail_password_opener, source_secrets_opener = libsodium_opening_adapters(source)
    slippage = hyperliquid_slippage_adapters(source)
    hyperliquid = hyperliquid_adapters()
    engine = sqlalchemy_adapters(source)
    simulation = sqlalchemy_simulation_adapters(source)
    messenger, inbox, start_link = telegram_adapters(source)
    mailer = smtp_adapters()
    outbox = SqlAlchemyOutboxAdapter(engine)
    links = dashboard_adapters(source)
    bot = bot_polling(inbox, lambda bot_inbox: telegram_bot(engine, bot_inbox, messenger, (outbox, links)))
    library_gateways = litellm_adapters()
    models: ModelGateways = {**library_gateways, **openrouter_adapters()}
    forecaster = forecaster_adapters(source)
    predictors = (models, forecaster)
    cycle_for = cycle_of(
        engine,
        (opener, provider_key_opener, source_secrets_opener),
        (environment, slippage, hyperliquid, simulation),
        (outbox, links),
        predictors,
    )
    for_tenant = worker_use_cases(
        engine,
        (opener, mail_password_opener),
        (environment, slippage, hyperliquid, simulation),
        (outbox, mailer, links),
        (cycle_for, source_systems(hyperliquid, forecaster), source_secrets_opener),
    )
    cycles = worker_cycles(engine, cycle_for, (hyperliquid, simulation))
    library_catalog = ReadModelCatalogUseCase(
        {name: gateway.model_catalog() for name, gateway in library_gateways.items()}
    )
    deliver = DeliverOutboxMessageUseCase(
        messenger, mailer, partial(mail_server_access_for, engine, mail_password_opener)
    )
    delivery = OutboxProcessing(ProcessOutboxUseCase(outbox, deliver).execute)
    daily = DailyChecks(
        ScheduleKeyExpiryChecksUseCase(
            apscheduler_daily_check_adapters(),
            SqlAlchemyTenantRepositoryAdapter(engine),
            partial(check_key_expiries, engine, (outbox, links)),
        ).execute
    )
    loops = WorkerLoops(bot, cycles, delivery, daily)
    return worker_api_adapters(source, for_tenant, loops, WorkerAnswers(start_link, library_catalog))


def telegram_bot(
    engine: SqlAlchemyEngine,
    inbox: BotInboxPort,
    messenger: MessengerPort,
    notifications: tuple[OutboxPort, NotificationLinkPort],
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
        SqlAlchemyLinkedChatLookupAdapter(engine), partial(notify_for, engine, *notifications), messenger
    )
    return BotPolling(AnswerBotMessagesUseCase(inbox, link_chat, test_notification).execute)


type SourcesData = tuple[SourceData, ...]


type WorkerCycle = RunCycleUseCase[CycleFlow, SourcesData, CycleContext, CycleDecisions, CycleOrder, object]


def worker_cycles(
    engine: SqlAlchemyEngine,
    cycle_for: Callable[[TenantId], WorkerCycle],
    markets: tuple[HyperliquidAdaptersOfInstallation, SimulatedExecution],
) -> CyclePolling:
    """Each round plans the cycles of the flows, records the actual price beside every expired forecast (R1.3.5), and
    settles the simulated positions on the real prices (R6.3.2)."""
    hyperliquid, simulation = markets
    *_, (real_orders, _), prices, _ = hyperliquid
    clock = system_clock_adapters()
    planned = ThreadsPlannedFlowsAdapter()
    plan = PlanFlowCyclesUseCase(
        SqlAlchemyScheduledFlowsAdapter(engine), planned, cycle_for, apscheduler_adapters(), clock
    )
    record_actual_prices = RecordActualPricesOfTenantsUseCase(
        prices, planned.tenants, partial(SqlAlchemyForecastRepositoryAdapter, engine)
    )
    settle_simulated_positions = SettleSimulatedPositionsUseCase(
        real_orders,
        SqlAlchemyTenantRepositoryAdapter(engine),
        lambda tenant_id: SqlAlchemySimulatedExchangeAdapter(engine, tenant_id, simulation),
    )

    def plan_round() -> None:
        plan.execute()
        record_actual_prices.execute(RecordActualPricesCommand(clock.now()))
        settle_simulated_positions.execute(SettleSimulatedPositionsCommand())

    return CyclePolling(plan_round)
