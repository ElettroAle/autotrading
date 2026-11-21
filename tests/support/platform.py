"""The platform as the scenarios see it: the use cases of a tenant built on the fake adapters, as bootstrap does."""

from collections.abc import Callable
from datetime import UTC, datetime
from secrets import token_hex
from uuid import UUID

from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import WorkerUseCases
from autotrading.adapters.outbound.hyperliquid.exchange import MARGIN_CURRENCY as HYPERLIQUID_SETTLEMENT_CURRENCY
from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand
from autotrading.application.flows.close_flow_positions import ClosingPorts
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.list_flow_summaries import ListFlowSummariesUseCase
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsUseCase
from autotrading.application.flows.pause_flows_on_expired_keys import (
    PauseFlowsOnExpiredKeysCommand,
    PauseFlowsOnExpiredKeysUseCase,
)
from autotrading.application.flows.ports import AccountRemovalPorts, FlowAccountPorts
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_account_transfers import ReadAccountTransfersUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_manual_closing import RecordManualClosingUseCase
from autotrading.application.flows.run_cycle_on_demand import CycleRun, RunCycleOnDemandCommand, RunCycleOnDemandUseCase
from autotrading.application.flows.select_model import SelectModelUseCase
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.check_key_expiries import CheckKeyExpiriesUseCase
from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.ports import BotMessage, LinkStores
from autotrading.application.notifications.send_test_email import SendTestEmailUseCase
from autotrading.application.notifications.send_test_notification import SendTestNotificationUseCase
from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.close_flow_position import CloseFlowPositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.application.sources.try_source_adapter import TrialServices, TrySourceAdapterUseCase
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.cycle_interval import DEFAULT_CYCLE_INTERVAL
from autotrading.domain.flows.emergency_closing import EmergencyClosing
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.account_state import FakeAccountStateAdapter
from tests.fakes.account_transfers import FakeAccountTransfersAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.alert_repository import AlertStore, InMemoryAlertRepositoryAdapter
from tests.fakes.bot_identity import FakeBotIdentityAdapter
from tests.fakes.bot_inbox import FakeBotInboxAdapter
from tests.fakes.channel_preferences_repository import (
    ChannelPreferencesStore,
    InMemoryChannelPreferencesRepositoryAdapter,
)
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.cycles import FakeClockAdapter, InMemoryCycleHistoryAdapter, InMemoryCycleRepositoryAdapter
from tests.fakes.email_test import FakeEmailTestAdapter
from tests.fakes.emergency_closing_log import InMemoryEmergencyClosingLogAdapter
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_forecasts import InMemoryFlowForecastsAdapter
from tests.fakes.flow_history import HistoryStore, InMemoryFlowHistoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_openings import InMemoryFlowOpeningsAdapter
from tests.fakes.flow_operations import InMemoryFlowOperationsAdapter
from tests.fakes.flow_repository import (
    FlowStore,
    InMemoryAutomaticPauseAdapter,
    InMemoryFlowRepositoryAdapter,
    InMemoryFlowTimingAdapter,
)
from tests.fakes.flow_status import FakeFlowStatusAdapter
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.key_expiries import (
    InMemoryKeyExpiriesAdapter,
    InMemoryKeyExpiryNoticeRepositoryAdapter,
    KeyExpiryNoticeStore,
)
from tests.fakes.ledger_recording import FakeLedgerRecordingAdapter
from tests.fakes.link_code_repository import (
    InMemoryLinkCodeLookupAdapter,
    InMemoryLinkCodeRepositoryAdapter,
    LinkCodeStore,
)
from tests.fakes.linked_chat_repository import (
    InMemoryLinkedChatLookupAdapter,
    InMemoryLinkedChatRepositoryAdapter,
    LinkedChatStore,
)
from tests.fakes.mailer import FakeMailerAdapter
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.notification_inbox import InboxStore, InMemoryNotificationInboxAdapter
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.notified_flows import InMemoryNotifiedFlowsAdapter
from tests.fakes.on_demand_cycles import FakeOnDemandCycleAdapter
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.position_closing import FakePositionClosingAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.provider_keys import (
    FakeProviderKeySealerAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.fakes.running_cycle import FakeRunningCycleAdapter
from tests.fakes.running_verifications import InMemoryRunningVerificationsAdapter
from tests.fakes.source_credentials import (
    FakeSourceSecretsOpenerAdapter,
    FakeSourceSecretsSealerAdapter,
    InMemorySourceCredentialsRepositoryAdapter,
    SourceCredentialsStore,
    SourceSecretsVault,
)
from tests.fakes.source_trials import FakeSourceTrialAdapter
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.fakes.verification import FakeVerificationAdapter
from tests.fakes.verification_run_repository import InMemoryVerificationRunRepositoryAdapter
from tests.support.activity import an_activity
from tests.support.credentials import hyperliquid_credentials
from tests.support.directory import Directory
from tests.support.mail_servers import MailServers
from tests.support.model_catalog import PLATFORM_MODELS
from tests.support.notifications import notification_inbox, notification_routes
from tests.support.procedure_orders import procedure_orders
from tests.support.source_selections import platform_systems

HYPERLIQUID = "Hyperliquid"
STARTED_AT = datetime(2026, 11, 10, 11, 59, 59, tzinfo=UTC)


def no_cycle_run_of(_tenant_id: TenantId) -> CycleRun:
    """A worker that composes no cycle: every instant asked for is already taken."""
    return lambda _command: None


def new_credentials() -> Credentials:
    return hyperliquid_credentials(account_address=f"0x{token_hex(20)}", secret_key=f"0x{token_hex(32)}")


class Platform:
    alerts: AlertStore
    inbox: InboxStore
    key_vault: ProviderKeyVault
    source_vault: SourceSecretsVault

    def __init__(self) -> None:
        self.directory = Directory()
        self.tenants = InMemoryTenantRepositoryAdapter()
        self.accounts = AccountStore()
        self.exchanges = {HYPERLIQUID: FakeExchangeAdapter()}
        self.vault: SealedVault = {}
        self.worker_reachable = True
        self.order_exchange = FakeOrderExchangeAdapter()
        self.orders: dict[TenantId, InMemoryOrderRepositoryAdapter] = {}
        self.slippage = Slippage.default()
        self.runs: dict[TenantId, InMemoryVerificationRunRepositoryAdapter] = {}
        # The keys of the AI providers and the credentials of the adapters of the sources, with what their private key
        # would open (R4.1.2).
        self.provider_keys, self.source_credentials = ProviderKeyStore(), SourceCredentialsStore()
        self.key_vault, self.source_vault = {}, {}
        self.flows = FlowStore()
        # The verifications in progress, by account and asset: what the database locks while one runs (ADR 0079).
        self.running_verifications: set[tuple[UUID, str]] = set()
        # The markets of the exchanges, and the adapters of the sources, the same in the API and in the worker
        # (R4.1.1): FlowCycles puts its own.
        self.markets, self.source_systems = {HYPERLIQUID: FakeMarketsAdapter()}, platform_systems()
        self.model_catalog: ModelCatalog = PLATFORM_MODELS
        self.link_codes: LinkCodeStore = {}
        self.chats: LinkedChatStore = {}
        self.messenger = FakeMessengerAdapter()
        self.emails: NotificationEmailStore = {}
        self.channel_preferences: ChannelPreferencesStore = {}
        self.mail_servers = MailServers()
        self.mailer = FakeMailerAdapter()
        # No dashboard to lead to unless a test names one (ADR destinazioni-delle-notifiche-nella-dashboard).
        self.links = FakeNotificationLinkAdapter(dashboard=False)
        # The state of the flows the notifications close with: none unless a test sets it (R3.5.4).
        self.flow_status = FakeFlowStatusAdapter()
        # The worker of the outbox is up: a notification is delivered as soon as it is queued.
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(
            DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.mail_servers.access_of).execute
        )
        self.bot_username: str | None = None
        self.activity_reader = FakeActivityReaderAdapter()
        # What the API reads of the accounts through the worker, and the orders the platform recorded (R1.6.1).
        self.account_activity = FakeAccountActivityAdapter()
        self.account_activity.unread = self.reading_on_exchange
        self.account_transfers = FakeAccountTransfersAdapter()
        # The stop loss and take profit on the exchange and those the platform recorded (R3.1.2).
        self.protection_exchange = FakeProtectionExchangeAdapter()
        self.protections = ProtectionStore()
        # The orders every tenant recorded are those the ledger reads, as the real adapter reads them from the table.
        self.platform_orders = InMemoryPlatformOrdersAdapter(
            self.protections, lambda: [order for orders in self.orders.values() for order in orders.orders]
        )
        self.ledger = InMemoryFlowLedgerAdapter()
        self.now = STARTED_AT
        self.running_cycles = FakeRunningCycleAdapter(lambda: len(self.order_exchange.sent))
        self.closed_positions = ClosedPositionStore()
        self.exit_plans = ExitPlanStore()
        self.cycles = InMemoryCycleRepositoryAdapter()
        self.equity_snapshots = EquitySnapshotStore()
        self.histories: dict[TenantId, InMemoryFlowHistoryAdapter] = {}
        # The readings of the accounts and the alarms on their balance, as the cycles of the worker leave them.
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.forecasts: dict[TenantId, InMemoryForecastRepositoryAdapter] = {}
        # The cycles the worker runs on request, with its clock: none until a scenario composes them (FlowCycles).
        self.worker_clock = FakeClockAdapter(STARTED_AT)
        self.cycle_run_of: Callable[[TenantId], CycleRun] = no_cycle_run_of
        # The emergency closings of every tenant, as their record keeps them (R3.2.3).
        self.emergency_closings: list[EmergencyClosing] = []
        # The alerts of every tenant, opened by the worker and read by the API (R6.2.3), and the bell of every tenant,
        # where the worker keeps each notification and the API reads it (R6.2.1), and the thresholds of the expiries of
        # the keys already told (R6.2.2).
        self.alerts, self.inbox, self.key_expiry_notices = {}, {}, KeyExpiryNoticeStore()
        # One exchange behind both ports: what the orders open is what the readings show.
        self.hyperliquid.trades_on(self.order_exchange)

    @property
    def hyperliquid(self) -> FakeExchangeAdapter:
        return self.exchanges[HYPERLIQUID]

    def user_id_of(self, user: str) -> UserId:
        return UserId(self.directory.person(user).object_id)

    def tenant_of(self, user: str) -> TenantId:
        command = ResolveTenantCommand(self.user_id_of(user))
        return ResolveTenantUseCase(self.tenants).execute(command)

    def accounts_of(self, user: str) -> list[Account]:
        return self.accounts.of(self.tenant_of(user))

    def accepted_credentials(self) -> Credentials:
        credentials = new_credentials()
        self.hyperliquid.accept(credentials)
        return credentials

    def register_account(self, user: str, command: RegisterAccountCommand) -> AccountRegistration:
        return self.use_cases_of(user).register_account.execute(command)

    def for_tenant(self, tenant_id: TenantId) -> TenantUseCases:
        """What bootstrap.for_tenant does, on the fake adapters."""
        account_state = FakeAccountStateAdapter(lambda: self.worker_for(tenant_id).read_exchange_state)
        position_closing = FakePositionClosingAdapter(lambda: self.worker_for(tenant_id).close_exchange_position)
        verification = FakeVerificationAdapter(lambda: self.worker_for(tenant_id).run_exchange_verification)
        on_demand_cycles = FakeOnDemandCycleAdapter(
            lambda flow_id: self.worker_for(tenant_id).run_cycle_on_demand.execute(RunCycleOnDemandCommand(flow_id))
        )
        source_trials = FakeSourceTrialAdapter(self.worker_for(tenant_id).try_source_adapter.execute)
        account_state.reachable = position_closing.reachable = verification.reachable = self.worker_reachable
        on_demand_cycles.reachable = source_trials.reachable = self.worker_reachable
        accounts = InMemoryAccountRepositoryAdapter(self.accounts, tenant_id)
        provider_keys = InMemoryProviderKeyRepositoryAdapter(self.provider_keys, tenant_id)
        flows = InMemoryFlowRepositoryAdapter(self.flows, tenant_id)
        flow_positions = CloseFlowPositionUseCase(position_closing)
        closed_positions = InMemoryClosedPositionRepositoryAdapter(self.closed_positions, tenant_id)
        flow_openings = InMemoryFlowOpeningsAdapter(self.orders_of(tenant_id))
        # The API hands its notifications to the worker, which holds the bot (ADR 0070).
        closing_notice = NotifyPositionClosedUseCase(
            NotifyFlowEventUseCase(self.worker_for(tenant_id).notify, self.flow_status), HYPERLIQUID_SETTLEMENT_CURRENCY
        )
        exit_plans = InMemoryExitPlanRepositoryAdapter(self.exit_plans, tenant_id)
        closing_ports = ClosingPorts(
            self.running_cycles, flow_positions, flow_openings, closed_positions, closing_notice, exit_plans
        )
        sources = ListSourcesUseCase(self.source_systems)
        source_credentials = InMemorySourceCredentialsRepositoryAdapter(self.source_credentials, tenant_id)
        ports = TenantPorts(
            accounts=accounts,
            allocated_capital=flows,
            sealer=self.sealer_of(tenant_id),
            exchanges=self.exchanges,
            account_state=account_state,
            position_closing=position_closing,
            manual_closings=RecordManualClosingUseCase(
                flows, flow_openings, closed_positions, closing_notice, exit_plans
            ),
            verification=verification,
            sources=sources,
            source_credentials=source_credentials,
            source_secrets_sealer=FakeSourceSecretsSealerAdapter(tenant_id, self.source_vault),
            source_trials=source_trials,
            provider_keys=provider_keys,
            provider_key_sealer=FakeProviderKeySealerAdapter(tenant_id, self.key_vault),
            provider_key_usage=flows,
            model_catalogs={"models": InMemoryModelCatalogAdapter(self.model_catalog)},
            flows=flows,
            running_verifications=InMemoryRunningVerificationsAdapter(self.running_verifications),
            flow_checks=FlowChecks(
                accounts=FlowAccountPorts(accounts, self.account_activity, self.ledger),
                markets=self.markets,
                models=SelectModelUseCase({"models": InMemoryModelCatalogAdapter(self.model_catalog)}, provider_keys),
                sources=SelectSourceUseCase(sources, source_credentials),
            ),
            flow_positions=flow_positions,
            closing_ports=closing_ports,
            account_removal=AccountRemovalPorts(account_state, accounts),
            account_activity=self.account_activity,
            account_transfers=self.account_transfers,
            flow_ledger=self.ledger,
            ledger_recording=FakeLedgerRecordingAdapter(
                RecordAccountExecutionsUseCase(flows, self.account_activity, self.platform_orders, self.ledger)
            ),
            on_demand_cycles=on_demand_cycles,
            flow_operations=InMemoryFlowOperationsAdapter(
                self.ledger,
                lambda: [account.id.value for account in accounts.list()],
                lambda: {flow.id: flow.name.value for flow in self.flows.flows},
            ),
            link_codes=InMemoryLinkCodeRepositoryAdapter(self.link_codes, tenant_id),
            bot_identity=FakeBotIdentityAdapter(self.bot_username),
            linked_chats=InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            notifier=self.worker_for(tenant_id).notify,
            flow_status=self.flow_status,
            notification_emails=InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id),
            mail_servers=self.mail_servers.repository(tenant_id),
            mail_password_sealer=self.mail_servers.sealer(tenant_id),
            email_tests=FakeEmailTestAdapter(self.worker_for(tenant_id).send_test_email.execute),
            channel_preferences=InMemoryChannelPreferencesRepositoryAdapter(self.channel_preferences, tenant_id),
            notified_flows=InMemoryNotifiedFlowsAdapter(self.flows, tenant_id),
            clock=lambda: self.now,
            closed_positions=closed_positions,
            exit_plans=exit_plans,
            cycle_history=InMemoryCycleHistoryAdapter(self.cycles, self.flows, tenant_id),
            decision_history=InMemoryCycleHistoryAdapter(self.cycles, self.flows, tenant_id),
            flow_directory=flows,
            flow_summaries=ListFlowSummariesUseCase(flows, accounts, InMemoryFlowTimingAdapter(self.flows, tenant_id)),
            flow_timing=InMemoryFlowTimingAdapter(self.flows, tenant_id),
            equity_snapshots=InMemoryEquitySnapshotRepositoryAdapter(self.equity_snapshots, tenant_id),
            openings_suspensions=InMemoryOpeningsSuspensionAdapter(self.flows, tenant_id),
            flow_forecasts=InMemoryFlowForecastsAdapter(self.forecasts_of(tenant_id)),
            historical_cycles=self.history_of(tenant_id),
            historical_closed_positions=self.history_of(tenant_id),
            historical_orders=self.history_of(tenant_id),
            reconciliation=self.readings,
            account_thresholds=accounts,
            account_names=accounts,
            automatic_pause=InMemoryAutomaticPauseAdapter(self.flows, tenant_id),
            emergency_closings=InMemoryEmergencyClosingLogAdapter(self.emergency_closings, tenant_id),
            alerts=self.alerts_of(tenant_id),
            alert_resolution=self.alerts_of(tenant_id),
            notification_inbox=self.inbox_of(tenant_id),
            environment="dev",
            settlement_currency=HYPERLIQUID_SETTLEMENT_CURRENCY,
        )
        return TenantUseCases.on(tenant_id, ports)

    def reading_on_exchange(self, account_id: UUID) -> AccountActivity:
        """What the worker reads of an account no test set a reading for: its balance on the exchange, as the worker
        reads it for the API (ADR 0044)."""
        if not self.worker_reachable:
            raise FlowExchangeUnavailableError
        account = next((each for each in self.accounts.accounts if each.id.value == account_id), None)
        if account is None:
            return an_activity()
        state = self.worker_for(account.tenant_id).read_exchange_state.execute(ReadExchangeStateCommand(account.id))
        return an_activity(balance=state.balance.amount, available_margin=state.available_margin.amount)

    def alerts_of(self, tenant_id: TenantId) -> InMemoryAlertRepositoryAdapter:
        """The alerts of the tenant: each tenant reads its own, as with row level security."""
        return InMemoryAlertRepositoryAdapter(self.alerts, tenant_id, lambda: self.now)

    def inbox_of(self, tenant_id: TenantId) -> InMemoryNotificationInboxAdapter:
        """The bell of the tenant: each tenant reads its own, as with row level security (R6.2.1)."""
        return InMemoryNotificationInboxAdapter(self.inbox, tenant_id, lambda: self.now)

    def history_of(self, tenant_id: TenantId) -> InMemoryFlowHistoryAdapter:
        """The histories of the tenant: each tenant reads its own store, as row level security does (R2.5.1)."""
        return self.histories.setdefault(tenant_id, InMemoryFlowHistoryAdapter(HistoryStore()))

    def forecasts_of(self, tenant_id: TenantId) -> InMemoryForecastRepositoryAdapter:
        """The forecasts the flows of the tenant recorded: each tenant reads its own, as row level security does."""
        return self.forecasts.setdefault(tenant_id, InMemoryForecastRepositoryAdapter())

    def worker_for(self, tenant_id: TenantId) -> WorkerUseCases:
        """What the worker builds for a request of the API, with the opener only it holds."""
        accounts = InMemoryAccountRepositoryAdapter(self.accounts, tenant_id)
        opener = FakeCredentialOpenerAdapter(self.vault)
        access = OpenTradingAccessUseCase(accounts, opener)
        order_exchanges, orders = {HYPERLIQUID: self.order_exchange}, self.orders_of(tenant_id)
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, self.exchanges)
        close_exchange_position = CloseExchangePositionUseCase(
            access, order_exchanges, orders, self.slippage, self.cancel_protections(tenant_id)
        )
        open_position = OpenPositionUseCase(access, order_exchanges, orders, self.slippage)
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=close_exchange_position,
            run_exchange_verification=RunExchangeVerificationUseCase(
                VerificationReadings(
                    ReadAccountForVerificationUseCase(accounts, opener, self.exchanges),
                    InMemoryFlowRepositoryAdapter(self.flows, tenant_id),
                ),
                procedure_orders(open_position, close_exchange_position, ReadMarketUseCase(access, order_exchanges)),
                self.runs_of(tenant_id),
                "dev",
                lambda: STARTED_AT,
            ),
            notify=self.notify_for(tenant_id),
            send_test_email=SendTestEmailUseCase(
                InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id),
                self.mail_servers.access_of(tenant_id),
                self.mailer,
            ),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, {HYPERLIQUID: self.activity_reader}),
            read_account_transfers=ReadAccountTransfersUseCase(accounts, opener, {HYPERLIQUID: self.activity_reader}),
            record_account_executions=RecordAccountExecutionsUseCase(
                InMemoryFlowRepositoryAdapter(self.flows, tenant_id),
                ReadAccountExecutionsUseCase(accounts, opener, {HYPERLIQUID: self.activity_reader}),
                self.platform_orders,
                self.ledger,
            ),
            run_cycle_on_demand=RunCycleOnDemandUseCase(
                InMemoryFlowRepositoryAdapter(self.flows, tenant_id),
                InMemoryFlowTimingAdapter(self.flows, tenant_id),
                self.worker_clock,
                self.cycle_run_of(tenant_id),
            ),
            try_source_adapter=TrySourceAdapterUseCase(
                self.source_systems,
                self.forecasts_of(tenant_id),
                OpenSourceCredentialsUseCase(
                    InMemorySourceCredentialsRepositoryAdapter(self.source_credentials, tenant_id),
                    FakeSourceSecretsOpenerAdapter(self.source_vault),
                ),
                TrialServices(ThreadPoolConcurrentCallsAdapter(), self.worker_clock, DEFAULT_CYCLE_INTERVAL),
            ),
        )

    def notify_for(self, tenant_id: TenantId) -> NotifyUseCase:
        """What the worker composes to queue the notifications of a tenant on the channels it chose (R3.5.3)."""
        return NotifyUseCase(
            InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id),
            self.mail_servers.repository(tenant_id),
            self.outbox,
            notification_routes(tenant_id, self.channel_preferences, self.links),
            notification_inbox(tenant_id, self.inbox, self.worker_clock),
        )

    def check_key_expiries(self, tenant_id: TenantId) -> None:
        """What the daily check of the worker runs for a tenant, on its clock (R6.2.2): bootstrap.check_key_expiries."""
        keys = InMemoryKeyExpiriesAdapter(
            self.accounts, self.provider_keys, self.flows, tenant_id, self.source_credentials
        )
        notify, alerts = self.notify_for(tenant_id), self.alerts_of(tenant_id)
        notices = InMemoryKeyExpiryNoticeRepositoryAdapter(self.key_expiry_notices, tenant_id)
        CheckKeyExpiriesUseCase(keys, notices, alerts, notify, self.worker_clock).execute()
        flows = InMemoryFlowRepositoryAdapter(self.flows, tenant_id)
        pause = PauseAffectedFlowsUseCase(
            flows,
            InMemoryAutomaticPauseAdapter(self.flows, tenant_id),
            NotifyFlowPausedUseCase(NotifyFlowEventUseCase(notify, self.flow_status), alerts),
        )
        PauseFlowsOnExpiredKeysUseCase(keys, flows, pause, self.worker_clock).execute(PauseFlowsOnExpiredKeysCommand())

    def cancel_protections(self, tenant_id: TenantId) -> CancelProtectionsUseCase:
        """What the worker runs after every closing: the protections of the position leave the exchange (R3.1.2)."""
        access = OpenTradingAccessUseCase(
            InMemoryAccountRepositoryAdapter(self.accounts, tenant_id), FakeCredentialOpenerAdapter(self.vault)
        )
        protections = InMemoryProtectionRepositoryAdapter(self.protections, tenant_id)
        return CancelProtectionsUseCase(access, {HYPERLIQUID: self.protection_exchange}, protections)

    def link_chat(self) -> LinkChatUseCase:
        """What the bot of the worker runs for every message it receives."""
        return LinkChatUseCase(
            InMemoryLinkCodeLookupAdapter(self.link_codes),
            lambda tenant_id: LinkStores(
                InMemoryLinkCodeRepositoryAdapter(self.link_codes, tenant_id),
                InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            ),
            self.messenger,
            lambda: self.now,
        )

    def bot_receives(self, chat_id: ChatId, text: str) -> None:
        """One round of the bot of the worker with this message waiting for it."""
        inbox = FakeBotInboxAdapter()
        inbox.waiting = [BotMessage(chat_id, text)]
        test_notification = SendTestNotificationUseCase(
            InMemoryLinkedChatLookupAdapter(self.chats),
            self.notify_for,
            self.messenger,
        )
        AnswerBotMessagesUseCase(inbox, self.link_chat(), test_notification).execute()

    def orders_of(self, tenant_id: TenantId) -> InMemoryOrderRepositoryAdapter:
        return self.orders.setdefault(tenant_id, InMemoryOrderRepositoryAdapter())

    def runs_of(self, tenant_id: TenantId) -> InMemoryVerificationRunRepositoryAdapter:
        return self.runs.setdefault(tenant_id, InMemoryVerificationRunRepositoryAdapter(self.running_verifications))

    def use_cases_of(self, user: str) -> TenantUseCases:
        return self.for_tenant(self.tenant_of(user))

    def sealer_of(self, tenant_id: TenantId) -> FakeCredentialSealerAdapter:
        return FakeCredentialSealerAdapter(tenant_id, self.vault)

    def uses_credentials(self, account: Account, credentials: Credentials) -> bool:
        """The fake seal is deterministic: sealing the same credentials again gives the saved text."""
        return account.credentials == self.sealer_of(account.tenant_id).seal(account.id, credentials)

    def account_named(self, user: str, name: str) -> Account:
        return next(account for account in self.accounts_of(user) if account.name.value == name)


def registration(name: str, exchange: str, credentials: Credentials) -> RegisterAccountCommand:
    return RegisterAccountCommand(name, exchange, credentials.values)
