from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.accounts.get_account import GetAccountUseCase
from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.application.accounts.list_supported_exchanges import ListSupportedExchangesUseCase
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    AccountStatePort,
    AllocatedCapitalPort,
    CredentialSealerPort,
    ExchangePort,
    VirtualBalancePort,
)
from autotrading.application.accounts.read_account_state import ReadAccountStateUseCase
from autotrading.application.accounts.register_account import RegisterAccountUseCase, RegistrationPorts
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsUseCase
from autotrading.application.accounts.reset_virtual_balance import ResetVirtualBalanceUseCase
from autotrading.application.accounts.set_account_key_expiry import SetAccountKeyExpiryUseCase
from autotrading.application.accounts.set_deviation_threshold import SetDeviationThresholdUseCase
from autotrading.application.agent.list_models import ListModelsUseCase
from autotrading.application.agent.list_provider_keys import ListProviderKeysUseCase
from autotrading.application.agent.model_gateways import ModelCatalogs
from autotrading.application.agent.ports import (
    ProviderKeyRepositoryPort,
    ProviderKeySealerPort,
    ProviderKeyUsagePort,
)
from autotrading.application.agent.register_provider_key import ProviderKeyServices, RegisterProviderKeyUseCase
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyUseCase
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyUseCase
from autotrading.application.agent.set_provider_key_expiry import SetProviderKeyExpiryUseCase
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.cash_out_profits import CashOutPorts, CashOutProfitsUseCase
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusUseCase
from autotrading.application.flows.close_flow_positions import CloseFlowPositionsUseCase, ClosingPorts
from autotrading.application.flows.close_in_emergency import CloseInEmergencyUseCase, EmergencyClosingPorts
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsUseCase
from autotrading.application.flows.confirm_reconciliation import ConfirmReconciliationUseCase
from autotrading.application.flows.create_flow import CreateFlowUseCase, FlowChecks
from autotrading.application.flows.duplicate_flow import DuplicateFlowUseCase
from autotrading.application.flows.export_account_operations import ExportAccountOperationsUseCase
from autotrading.application.flows.export_flow_operations import ExportFlowOperationsUseCase
from autotrading.application.flows.export_flow_strategy import ExportFlowStrategyUseCase
from autotrading.application.flows.get_flow import GetFlowUseCase
from autotrading.application.flows.get_flow_version import GetFlowVersionUseCase
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyUseCase
from autotrading.application.flows.list_account_capital_changes import ListAccountCapitalChangesUseCase
from autotrading.application.flows.list_account_operations import ListAccountOperationsUseCase
from autotrading.application.flows.list_capital_changes import ListCapitalChangesUseCase
from autotrading.application.flows.list_closed_positions import ListClosedPositionsUseCase
from autotrading.application.flows.list_cycles import ListCyclesUseCase
from autotrading.application.flows.list_decisions import ListDecisionsUseCase
from autotrading.application.flows.list_emergency_flows import ListEmergencyFlowsUseCase
from autotrading.application.flows.list_flow_operations import ListFlowOperationsUseCase
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsUseCase
from autotrading.application.flows.list_flow_versions import ListFlowVersionsUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.list_reconciliation_alarms import ListReconciliationAlarmsUseCase
from autotrading.application.flows.list_tradable_assets import ListTradableAssetsUseCase
from autotrading.application.flows.list_unattributable import ListUnattributableUseCase
from autotrading.application.flows.modify_flow import ModifyFlowUseCase
from autotrading.application.flows.ports import (
    AccountActivityPort,
    AccountDeviationThresholdPort,
    AccountRemovalPorts,
    AccountTransfersPort,
    AlertResolutionPort,
    AutomaticPausePort,
    ClosedPositionRepositoryPort,
    CycleHistoryPort,
    DecisionHistoryPort,
    EmergencyClosingLogPort,
    EquitySnapshotRepositoryPort,
    ExitPlanRepositoryPort,
    FlowAccountNamePort,
    FlowDirectoryPort,
    FlowForecastsPort,
    FlowLedgerPort,
    FlowOperationsPort,
    FlowPositionsPort,
    FlowRepositoryPort,
    FlowSummaryPort,
    FlowTimingPort,
    HistoricalClosedPositionsPort,
    HistoricalCyclesPort,
    HistoricalOrdersPort,
    LedgerRecordingPort,
    OnDemandCyclePort,
    OpeningsSuspensionPort,
    PastDecisionsPort,
    ReconciliationRepositoryPort,
    RunningVerificationsPort,
)
from autotrading.application.flows.preview_emergency_closing import PreviewEmergencyClosingUseCase
from autotrading.application.flows.query_closed_position_history import QueryClosedPositionHistoryUseCase
from autotrading.application.flows.query_cycle_history import QueryCycleHistoryUseCase
from autotrading.application.flows.query_order_history import QueryOrderHistoryUseCase
from autotrading.application.flows.rank_flows import RankFlowsUseCase
from autotrading.application.flows.read_account_reconciliation import ReadAccountReconciliationUseCase
from autotrading.application.flows.read_cycle import ReadCycleUseCase
from autotrading.application.flows.read_default_system_prompt import ReadDefaultSystemPromptUseCase
from autotrading.application.flows.read_flow_cost import ReadFlowCostUseCase
from autotrading.application.flows.read_flow_equity import ReadFlowEquityUseCase
from autotrading.application.flows.read_flow_memory import ReadFlowMemoryUseCase
from autotrading.application.flows.read_flow_results import FlowPeriodPorts, ReadFlowResultsUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsUseCase
from autotrading.application.flows.read_forecast_accuracy import ReadForecastAccuracyUseCase
from autotrading.application.flows.read_free_capital import ReadFreeCapitalUseCase
from autotrading.application.flows.read_last_decision import ReadLastDecisionUseCase
from autotrading.application.flows.read_next_cycle import ReadNextCycleUseCase
from autotrading.application.flows.read_openings_suspension import ReadOpeningsSuspensionUseCase
from autotrading.application.flows.remove_account_with_flows import RemoveAccountWithFlowsUseCase
from autotrading.application.flows.request_on_demand_cycle import RequestOnDemandCycleUseCase
from autotrading.application.flows.resume_flow_openings import ResumeFlowOpeningsUseCase
from autotrading.application.flows.stop_flow import StopFlowUseCase
from autotrading.application.notifications.choose_notification_channel import ChooseNotificationChannelUseCase
from autotrading.application.notifications.count_open_alerts import CountOpenAlertsUseCase
from autotrading.application.notifications.count_unread_notifications import CountUnreadNotificationsUseCase
from autotrading.application.notifications.get_alert import GetAlertUseCase
from autotrading.application.notifications.get_linked_chat import GetLinkedChatUseCase
from autotrading.application.notifications.get_mail_server import GetMailServerUseCase
from autotrading.application.notifications.get_notification_channels import GetNotificationChannelsUseCase
from autotrading.application.notifications.get_notification_email import GetNotificationEmailUseCase
from autotrading.application.notifications.list_alerts import ListAlertsUseCase
from autotrading.application.notifications.list_inbox_notifications import ListInboxNotificationsUseCase
from autotrading.application.notifications.mark_all_notifications_read import MarkAllNotificationsReadUseCase
from autotrading.application.notifications.mark_notification_read import MarkNotificationReadUseCase
from autotrading.application.notifications.notify_cash_out_done import NotifyCashOutDoneUseCase
from autotrading.application.notifications.notify_emergency_closing_done import NotifyEmergencyClosingDoneUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.ports import (
    AlertRepositoryPort,
    BotStartLinkPort,
    ChannelPreferencesRepositoryPort,
    EmailTestPort,
    FlowStatusPort,
    LinkCodeRepositoryPort,
    LinkedChatRepositoryPort,
    MailPasswordSealerPort,
    MailServerRepositoryPort,
    NotificationEmailRepositoryPort,
    NotificationInboxPort,
    NotifiedFlowsPort,
    NotifierPort,
)
from autotrading.application.notifications.remove_flow_channel_exception import (
    RemoveFlowChannelExceptionUseCase,
)
from autotrading.application.notifications.remove_mail_server import RemoveMailServerUseCase
from autotrading.application.notifications.remove_notification_email import RemoveNotificationEmailUseCase
from autotrading.application.notifications.request_link_code import RequestLinkCodeUseCase
from autotrading.application.notifications.request_test_email import RequestTestEmailUseCase
from autotrading.application.notifications.resolve_alert import ResolveAlertUseCase
from autotrading.application.notifications.send_linked_chat_test_notification import (
    SendLinkedChatTestNotificationUseCase,
)
from autotrading.application.notifications.set_flow_channel_exception import SetFlowChannelExceptionUseCase
from autotrading.application.notifications.set_mail_server import SetMailServerUseCase
from autotrading.application.notifications.set_notification_email import SetNotificationEmailUseCase
from autotrading.application.notifications.unlink_chat import UnlinkChatUseCase
from autotrading.application.orders.close_position import ClosePositionUseCase
from autotrading.application.orders.ports import ManualClosingRecorderPort, PositionClosingPort
from autotrading.application.sources.configure_source_adapter import ConfigureSourceAdapterUseCase
from autotrading.application.sources.get_source import GetSourceUseCase
from autotrading.application.sources.list_source_credentials import ListSourceCredentialsUseCase
from autotrading.application.sources.list_source_offers import ListSourceOffersUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.sources.ports import (
    SourceCredentialsRepositoryPort,
    SourceSecretsSealerPort,
    SourceTrialPort,
)
from autotrading.application.sources.remove_source_credentials import RemoveSourceCredentialsUseCase
from autotrading.application.sources.request_source_trial import RequestSourceTrialUseCase
from autotrading.application.sources.set_source_credentials_expiry import SetSourceCredentialsExpiryUseCase
from autotrading.application.verification.ports import VerificationPort
from autotrading.application.verification.run_verification import RunVerificationUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class TenantPorts:
    """The adapters of one request, bound to its tenant, that the use cases of the API run on."""

    accounts: AccountRepositoryPort
    allocated_capital: AllocatedCapitalPort
    sealer: CredentialSealerPort
    exchanges: Mapping[str, ExchangePort]
    # The exchanges among them that hold a virtual balance instead of funds (R6.3.2).
    virtual_balances: Mapping[str, VirtualBalancePort]
    account_state: AccountStatePort
    position_closing: PositionClosingPort
    manual_closings: ManualClosingRecorderPort
    verification: VerificationPort
    # The sources with the adapters the installation composes (R4.1.1).
    sources: ListSourcesUseCase
    # The credentials the tenant gave the adapters of the sources, and their seal: the API never opens them (R4.1.2).
    source_credentials: SourceCredentialsRepositoryPort
    source_secrets_sealer: SourceSecretsSealerPort
    # The trial of an adapter, run by the worker, which alone opens the credentials (R6.3.1).
    source_trials: SourceTrialPort
    provider_keys: ProviderKeyRepositoryPort
    provider_key_sealer: ProviderKeySealerPort
    provider_key_usage: ProviderKeyUsagePort
    model_catalogs: ModelCatalogs
    flows: FlowRepositoryPort
    running_verifications: RunningVerificationsPort
    flow_checks: FlowChecks
    flow_positions: FlowPositionsPort
    closing_ports: ClosingPorts
    account_removal: AccountRemovalPorts
    account_activity: AccountActivityPort
    account_transfers: AccountTransfersPort
    flow_ledger: FlowLedgerPort
    ledger_recording: LedgerRecordingPort
    on_demand_cycles: OnDemandCyclePort
    flow_operations: FlowOperationsPort
    link_codes: LinkCodeRepositoryPort
    bot_identity: BotStartLinkPort
    linked_chats: LinkedChatRepositoryPort
    notifier: NotifierPort
    flow_status: FlowStatusPort
    notification_emails: NotificationEmailRepositoryPort
    mail_servers: MailServerRepositoryPort
    mail_password_sealer: MailPasswordSealerPort
    email_tests: EmailTestPort
    channel_preferences: ChannelPreferencesRepositoryPort
    notified_flows: NotifiedFlowsPort
    clock: Callable[[], datetime]
    closed_positions: ClosedPositionRepositoryPort
    exit_plans: ExitPlanRepositoryPort
    cycle_history: CycleHistoryPort
    decision_history: DecisionHistoryPort
    flow_directory: FlowDirectoryPort
    flow_summaries: FlowSummaryPort
    flow_timing: FlowTimingPort
    # The decisions of the flows with what came of them, that the memory of a flow holds (R5.3.4).
    past_decisions: PastDecisionsPort
    equity_snapshots: EquitySnapshotRepositoryPort
    openings_suspensions: OpeningsSuspensionPort
    flow_forecasts: FlowForecastsPort
    historical_cycles: HistoricalCyclesPort
    historical_closed_positions: HistoricalClosedPositionsPort
    historical_orders: HistoricalOrdersPort
    reconciliation: ReconciliationRepositoryPort
    account_thresholds: AccountDeviationThresholdPort
    account_names: FlowAccountNamePort
    automatic_pause: AutomaticPausePort
    emergency_closings: EmergencyClosingLogPort
    alerts: AlertRepositoryPort
    alert_resolution: AlertResolutionPort
    notification_inbox: NotificationInboxPort
    environment: str
    settlement_currency: str


@dataclass(frozen=True, slots=True)
class TenantUseCases:
    """The use cases of one request, built by bootstrap.for_tenant on adapters bound to the tenant of the request."""

    register_account: RegisterAccountUseCase
    reset_virtual_balance: ResetVirtualBalanceUseCase
    list_accounts: ListAccountsUseCase
    list_supported_exchanges: ListSupportedExchangesUseCase
    get_account: GetAccountUseCase
    replace_credentials: ReplaceCredentialsUseCase
    set_account_key_expiry: SetAccountKeyExpiryUseCase
    read_account_state: ReadAccountStateUseCase
    remove_account_with_flows: RemoveAccountWithFlowsUseCase
    close_position: ClosePositionUseCase
    run_verification: RunVerificationUseCase
    list_sources: ListSourcesUseCase
    list_source_offers: ListSourceOffersUseCase
    get_source: GetSourceUseCase
    list_source_credentials: ListSourceCredentialsUseCase
    configure_source_adapter: ConfigureSourceAdapterUseCase
    remove_source_credentials: RemoveSourceCredentialsUseCase
    set_source_credentials_expiry: SetSourceCredentialsExpiryUseCase
    request_source_trial: RequestSourceTrialUseCase
    register_provider_key: RegisterProviderKeyUseCase
    replace_provider_key: ReplaceProviderKeyUseCase
    remove_provider_key: RemoveProviderKeyUseCase
    list_provider_keys: ListProviderKeysUseCase
    set_provider_key_expiry: SetProviderKeyExpiryUseCase
    list_models: ListModelsUseCase
    create_flow: CreateFlowUseCase
    list_flows: ListFlowsUseCase
    get_flow: GetFlowUseCase
    read_default_system_prompt: ReadDefaultSystemPromptUseCase
    list_tradable_assets: ListTradableAssetsUseCase
    read_free_capital: ReadFreeCapitalUseCase
    read_flow_memory: ReadFlowMemoryUseCase
    read_flow_results: ReadFlowResultsUseCase
    request_link_code: RequestLinkCodeUseCase
    get_linked_chat: GetLinkedChatUseCase
    unlink_chat: UnlinkChatUseCase
    send_test_notification: SendLinkedChatTestNotificationUseCase
    get_notification_email: GetNotificationEmailUseCase
    set_notification_email: SetNotificationEmailUseCase
    remove_notification_email: RemoveNotificationEmailUseCase
    request_test_email: RequestTestEmailUseCase
    get_mail_server: GetMailServerUseCase
    set_mail_server: SetMailServerUseCase
    remove_mail_server: RemoveMailServerUseCase
    get_notification_channels: GetNotificationChannelsUseCase
    choose_notification_channel: ChooseNotificationChannelUseCase
    set_flow_channel_exception: SetFlowChannelExceptionUseCase
    remove_flow_channel_exception: RemoveFlowChannelExceptionUseCase
    modify_flow: ModifyFlowUseCase
    get_flow_version: GetFlowVersionUseCase
    list_flow_versions: ListFlowVersionsUseCase
    compare_flow_versions: CompareFlowVersionsUseCase
    change_flow_status: ChangeFlowStatusUseCase
    archive_flow: ArchiveFlowUseCase
    stop_flow: StopFlowUseCase
    cash_out_profits: CashOutProfitsUseCase
    change_allocated_capital: ChangeAllocatedCapitalUseCase
    list_capital_changes: ListCapitalChangesUseCase
    list_account_capital_changes: ListAccountCapitalChangesUseCase
    list_closed_positions: ListClosedPositionsUseCase
    list_flow_operations: ListFlowOperationsUseCase
    list_account_operations: ListAccountOperationsUseCase
    export_flow_operations: ExportFlowOperationsUseCase
    export_account_operations: ExportAccountOperationsUseCase
    list_cycles: ListCyclesUseCase
    read_cycle: ReadCycleUseCase
    read_last_decision: ReadLastDecisionUseCase
    request_on_demand_cycle: RequestOnDemandCycleUseCase
    list_decisions: ListDecisionsUseCase
    read_flow_cost: ReadFlowCostUseCase
    read_flow_statistics: ReadFlowStatisticsUseCase
    read_forecast_accuracy: ReadForecastAccuracyUseCase
    list_flow_overviews: ListFlowOverviewsUseCase
    read_flow_equity: ReadFlowEquityUseCase
    duplicate_flow: DuplicateFlowUseCase
    query_cycle_history: QueryCycleHistoryUseCase
    query_closed_position_history: QueryClosedPositionHistoryUseCase
    query_order_history: QueryOrderHistoryUseCase
    export_flow_strategy: ExportFlowStrategyUseCase
    import_flow_strategy: ImportFlowStrategyUseCase
    rank_flows: RankFlowsUseCase
    resume_flow_openings: ResumeFlowOpeningsUseCase
    set_deviation_threshold: SetDeviationThresholdUseCase
    read_account_reconciliation: ReadAccountReconciliationUseCase
    list_reconciliation_alarms: ListReconciliationAlarmsUseCase
    list_unattributable: ListUnattributableUseCase
    confirm_reconciliation: ConfirmReconciliationUseCase
    close_in_emergency: CloseInEmergencyUseCase
    preview_emergency_closing: PreviewEmergencyClosingUseCase
    list_alerts: ListAlertsUseCase
    count_open_alerts: CountOpenAlertsUseCase
    get_alert: GetAlertUseCase
    resolve_alert: ResolveAlertUseCase
    list_inbox_notifications: ListInboxNotificationsUseCase
    count_unread_notifications: CountUnreadNotificationsUseCase
    mark_notification_read: MarkNotificationReadUseCase
    mark_all_notifications_read: MarkAllNotificationsReadUseCase

    @classmethod
    def on(cls, tenant_id: TenantId, ports: TenantPorts) -> TenantUseCases:
        accounts, sealer, exchanges = ports.accounts, ports.sealer, ports.exchanges
        keys = ports.provider_keys
        source_offers = ListSourceOffersUseCase(ports.sources, ports.source_credentials)
        key_services = ProviderKeyServices(ports.model_catalogs, ports.provider_key_sealer)
        return cls(
            register_account=RegisterAccountUseCase(
                tenant_id, RegistrationPorts(accounts, sealer, exchanges, ports.virtual_balances)
            ),
            reset_virtual_balance=ResetVirtualBalanceUseCase(accounts, ports.virtual_balances),
            list_accounts=ListAccountsUseCase(
                accounts, ports.allocated_capital, exchanges, ports.settlement_currency, ports.clock
            ),
            list_supported_exchanges=ListSupportedExchangesUseCase(exchanges, ports.virtual_balances),
            get_account=GetAccountUseCase(
                accounts, ports.allocated_capital, exchanges, ports.settlement_currency, ports.clock
            ),
            replace_credentials=ReplaceCredentialsUseCase(accounts, sealer, exchanges),
            set_account_key_expiry=SetAccountKeyExpiryUseCase(accounts, exchanges),
            read_account_state=ReadAccountStateUseCase(accounts, ports.account_state),
            remove_account_with_flows=RemoveAccountWithFlowsUseCase(
                ports.flows,
                ports.account_removal,
                StopFlowUseCase(ports.flows, CloseFlowPositionsUseCase(ports.closing_ports), ports.alert_resolution),
                ArchiveFlowUseCase(ports.flows, ports.alert_resolution),
            ),
            close_position=ClosePositionUseCase(ports.position_closing, ports.manual_closings),
            run_verification=RunVerificationUseCase(ports.verification),
            list_sources=ports.sources,
            list_source_offers=source_offers,
            get_source=GetSourceUseCase(source_offers),
            list_source_credentials=ListSourceCredentialsUseCase(ports.sources, ports.source_credentials, ports.clock),
            configure_source_adapter=ConfigureSourceAdapterUseCase(
                tenant_id, ports.sources, ports.source_credentials, ports.source_secrets_sealer
            ),
            remove_source_credentials=RemoveSourceCredentialsUseCase(ports.source_credentials),
            set_source_credentials_expiry=SetSourceCredentialsExpiryUseCase(ports.source_credentials),
            request_source_trial=RequestSourceTrialUseCase(ports.sources, ports.source_trials),
            register_provider_key=RegisterProviderKeyUseCase(tenant_id, keys, key_services),
            replace_provider_key=ReplaceProviderKeyUseCase(keys, key_services),
            remove_provider_key=RemoveProviderKeyUseCase(keys, ports.provider_key_usage),
            list_provider_keys=ListProviderKeysUseCase(keys, ports.model_catalogs, ports.clock),
            set_provider_key_expiry=SetProviderKeyExpiryUseCase(keys, ports.model_catalogs),
            list_models=ListModelsUseCase(ports.model_catalogs, keys),
            create_flow=CreateFlowUseCase(tenant_id, ports.flows, ports.flow_checks),
            list_flows=ListFlowsUseCase(ports.flows),
            get_flow=GetFlowUseCase(ports.flows),
            read_default_system_prompt=ReadDefaultSystemPromptUseCase(),
            list_tradable_assets=ListTradableAssetsUseCase(ports.flow_checks.markets),
            read_free_capital=ReadFreeCapitalUseCase(ports.flows, ports.flow_checks.accounts),
            read_flow_memory=ReadFlowMemoryUseCase(
                ports.flows, ports.past_decisions, ports.account_activity, ports.clock
            ),
            read_flow_results=ReadFlowResultsUseCase(
                ReadFlowStateUseCase(ports.flows, ports.account_activity, ports.flow_ledger, ports.exit_plans),
                ReadOpeningsSuspensionUseCase(
                    ports.flows, ports.openings_suspensions, ports.reconciliation, ports.account_names, ports.clock
                ),
                ReadNextCycleUseCase(ports.flows, ports.flow_timing, ports.clock),
                FlowPeriodPorts(ports.equity_snapshots, ports.cycle_history),
                ports.clock,
            ),
            request_link_code=RequestLinkCodeUseCase(tenant_id, ports.link_codes, ports.bot_identity, ports.clock),
            get_linked_chat=GetLinkedChatUseCase(ports.linked_chats),
            unlink_chat=UnlinkChatUseCase(ports.linked_chats),
            send_test_notification=SendLinkedChatTestNotificationUseCase(ports.linked_chats, ports.notifier),
            get_notification_email=GetNotificationEmailUseCase(ports.notification_emails, ports.mail_servers),
            set_notification_email=SetNotificationEmailUseCase(tenant_id, ports.notification_emails),
            remove_notification_email=RemoveNotificationEmailUseCase(ports.notification_emails),
            request_test_email=RequestTestEmailUseCase(
                ports.notification_emails, ports.mail_servers, ports.email_tests
            ),
            get_mail_server=GetMailServerUseCase(ports.mail_servers),
            set_mail_server=SetMailServerUseCase(tenant_id, ports.mail_servers, ports.mail_password_sealer),
            remove_mail_server=RemoveMailServerUseCase(ports.mail_servers),
            get_notification_channels=GetNotificationChannelsUseCase(
                ports.channel_preferences,
                ports.notified_flows,
                ports.linked_chats,
                ports.notification_emails,
                ports.mail_servers,
            ),
            choose_notification_channel=ChooseNotificationChannelUseCase(ports.channel_preferences),
            set_flow_channel_exception=SetFlowChannelExceptionUseCase(ports.channel_preferences, ports.notified_flows),
            remove_flow_channel_exception=RemoveFlowChannelExceptionUseCase(ports.channel_preferences),
            modify_flow=ModifyFlowUseCase(ports.flows, ports.flow_checks, ports.account_activity),
            get_flow_version=GetFlowVersionUseCase(ports.flows),
            list_flow_versions=ListFlowVersionsUseCase(ports.flows),
            compare_flow_versions=CompareFlowVersionsUseCase(ports.flows),
            change_flow_status=ChangeFlowStatusUseCase(
                ports.flows, ports.running_verifications, ports.flow_checks.accounts, ports.alert_resolution
            ),
            archive_flow=ArchiveFlowUseCase(ports.flows, ports.alert_resolution),
            stop_flow=StopFlowUseCase(
                ports.flows, CloseFlowPositionsUseCase(ports.closing_ports), ports.alert_resolution
            ),
            cash_out_profits=CashOutProfitsUseCase(
                ports.flows,
                CashOutPorts(
                    ReadFlowStateUseCase(ports.flows, ports.account_activity, ports.flow_ledger, ports.exit_plans),
                    CloseFlowPositionsUseCase(ports.closing_ports),
                    ports.ledger_recording,
                    ports.clock,
                    NotifyCashOutDoneUseCase(
                        NotifyFlowEventUseCase(ports.notifier, ports.flow_status), ports.settlement_currency
                    ),
                ),
            ),
            change_allocated_capital=ChangeAllocatedCapitalUseCase(
                ports.flows,
                ports.flow_checks.accounts,
                ReadFlowStateUseCase(ports.flows, ports.account_activity, ports.flow_ledger, ports.exit_plans),
                ports.clock,
            ),
            list_capital_changes=ListCapitalChangesUseCase(ports.flows, ports.settlement_currency),
            list_account_capital_changes=ListAccountCapitalChangesUseCase(
                ports.flows, ports.account_transfers, ports.settlement_currency
            ),
            list_closed_positions=ListClosedPositionsUseCase(ports.flows, ports.closed_positions),
            list_flow_operations=ListFlowOperationsUseCase(ports.flows, ports.flow_operations),
            list_account_operations=ListAccountOperationsUseCase(ports.flow_operations),
            export_flow_operations=ExportFlowOperationsUseCase(ports.flows, ports.flow_operations),
            export_account_operations=ExportAccountOperationsUseCase(ports.flow_operations),
            list_cycles=ListCyclesUseCase(ports.flow_directory, ports.cycle_history),
            read_cycle=ReadCycleUseCase(ports.flow_directory, ports.cycle_history),
            read_last_decision=ReadLastDecisionUseCase(ports.flow_directory, ports.cycle_history),
            request_on_demand_cycle=RequestOnDemandCycleUseCase(ports.flows, ports.on_demand_cycles),
            list_decisions=ListDecisionsUseCase(ports.flow_directory, ports.decision_history, ports.clock),
            read_flow_cost=ReadFlowCostUseCase(ports.flow_directory, ports.cycle_history),
            read_flow_statistics=ReadFlowStatisticsUseCase(
                ports.flows, ports.closed_positions, ports.cycle_history, ports.equity_snapshots, ports.clock
            ),
            read_forecast_accuracy=ReadForecastAccuracyUseCase(ports.flows, ports.flow_forecasts, ports.clock),
            list_flow_overviews=ListFlowOverviewsUseCase(
                ports.flow_summaries,
                ports.cycle_history,
                ReadFlowResultsUseCase(
                    ReadFlowStateUseCase(ports.flows, ports.account_activity, ports.flow_ledger, ports.exit_plans),
                    ReadOpeningsSuspensionUseCase(
                        ports.flows, ports.openings_suspensions, ports.reconciliation, ports.account_names, ports.clock
                    ),
                    ReadNextCycleUseCase(ports.flows, ports.flow_timing, ports.clock),
                    FlowPeriodPorts(ports.equity_snapshots, ports.cycle_history),
                    ports.clock,
                ),
                ports.environment,
                ports.clock,
            ),
            read_flow_equity=ReadFlowEquityUseCase(ports.flows, ports.equity_snapshots, ports.clock),
            duplicate_flow=DuplicateFlowUseCase(ports.flows),
            query_cycle_history=QueryCycleHistoryUseCase(ports.historical_cycles, ports.clock),
            query_closed_position_history=QueryClosedPositionHistoryUseCase(
                ports.historical_closed_positions, ports.clock
            ),
            query_order_history=QueryOrderHistoryUseCase(ports.historical_orders, ports.clock),
            export_flow_strategy=ExportFlowStrategyUseCase(ports.flows),
            import_flow_strategy=ImportFlowStrategyUseCase(
                tenant_id, ports.flows, ports.flow_checks.models, ports.flow_checks.sources
            ),
            rank_flows=RankFlowsUseCase(
                ports.flows, ports.equity_snapshots, ports.closed_positions, ports.cycle_history, ports.clock
            ),
            resume_flow_openings=ResumeFlowOpeningsUseCase(ports.flows, ports.openings_suspensions, ports.clock),
            set_deviation_threshold=SetDeviationThresholdUseCase(accounts),
            read_account_reconciliation=ReadAccountReconciliationUseCase(
                ports.reconciliation, ports.account_thresholds
            ),
            list_reconciliation_alarms=ListReconciliationAlarmsUseCase(ports.reconciliation, ports.account_names),
            list_unattributable=ListUnattributableUseCase(ports.reconciliation, ports.account_names),
            confirm_reconciliation=ConfirmReconciliationUseCase(
                ports.reconciliation, ports.account_names, ports.clock, ports.alert_resolution
            ),
            close_in_emergency=CloseInEmergencyUseCase(
                tenant_id,
                EmergencyClosingPorts(
                    ListEmergencyFlowsUseCase(ports.flows, ports.account_names),
                    ports.automatic_pause,
                    CloseFlowPositionsUseCase(ports.closing_ports),
                    ports.emergency_closings,
                    ports.clock,
                    NotifyEmergencyClosingDoneUseCase(ports.notifier),
                ),
            ),
            preview_emergency_closing=PreviewEmergencyClosingUseCase(
                ListEmergencyFlowsUseCase(ports.flows, ports.account_names), ports.account_activity
            ),
            list_alerts=ListAlertsUseCase(ports.alerts),
            count_open_alerts=CountOpenAlertsUseCase(ports.alerts),
            get_alert=GetAlertUseCase(ports.alerts),
            resolve_alert=ResolveAlertUseCase(ports.alerts),
            list_inbox_notifications=ListInboxNotificationsUseCase(ports.notification_inbox),
            count_unread_notifications=CountUnreadNotificationsUseCase(ports.notification_inbox),
            mark_notification_read=MarkNotificationReadUseCase(ports.notification_inbox),
            mark_all_notifications_read=MarkAllNotificationsReadUseCase(ports.notification_inbox),
        )
