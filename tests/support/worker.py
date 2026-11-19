"""The worker of an installation, in memory, for the tests of the internal HTTP contract (ADR 0021, ADR 0023)."""

from datetime import UTC, datetime
from decimal import Decimal
from secrets import token_hex

from autotrading.adapters.inbound.api.worker import WorkerUseCases
from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_account_transfers import ReadAccountTransfersUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.run_cycle import RunCycleCommand
from autotrading.application.flows.run_cycle_on_demand import CycleRun, RunCycleOnDemandUseCase
from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.send_test_email import SendTestEmailUseCase
from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.application.sources.try_source_adapter import TrialServices, TrySourceAdapterUseCase
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.flows.cycle_interval import DEFAULT_CYCLE_INTERVAL
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.channel_preferences_repository import ChannelPreferencesStore
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.cycles import FakeClockAdapter
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.mailer import FakeMailerAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.notification_inbox import InboxStore
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.source_credentials import (
    FakeSourceSecretsOpenerAdapter,
    InMemorySourceCredentialsRepositoryAdapter,
    SourceCredentialsStore,
    SourceSecretsVault,
)
from tests.fakes.verification_run_repository import InMemoryVerificationRunRepositoryAdapter
from tests.support.accounts import an_account
from tests.support.mail_servers import MailServers
from tests.support.notifications import notification_inbox, notification_routes
from tests.support.platform import HYPERLIQUID, new_credentials
from tests.support.procedure_orders import procedure_orders
from tests.support.source_selections import platform_systems

TOKEN = token_hex(16)
STARTED_AT = datetime(2026, 11, 10, 11, 59, 59, tzinfo=UTC)
TENANT = TenantId.new()


class Worker:
    """The worker of an installation: its store, its exchange and the vault only its opener reads."""

    def __init__(self) -> None:
        self.store = AccountStore()
        self.vault: SealedVault = {}
        self.exchange = FakeExchangeAdapter()
        self.order_exchange = FakeOrderExchangeAdapter()
        self.orders = InMemoryOrderRepositoryAdapter()
        self.runs = InMemoryVerificationRunRepositoryAdapter()
        self.flows = FlowStore()
        self.chats: LinkedChatStore = {}
        self.messenger = FakeMessengerAdapter()
        self.emails: NotificationEmailStore = {}
        self.channel_preferences: ChannelPreferencesStore = {}
        self.mail_servers = MailServers()
        self.mailer = FakeMailerAdapter()
        # No dashboard to lead to unless a test names one (ADR destinazioni-delle-notifiche-nella-dashboard).
        self.links = FakeNotificationLinkAdapter(dashboard=False)
        # The worker of the outbox is up: a notification is delivered as soon as it is queued.
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(
            DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.mail_servers.access_of).execute
        )
        self.activity_reader = FakeActivityReaderAdapter()
        self.protection_exchange = FakeProtectionExchangeAdapter()
        self.protections = ProtectionStore()
        self.platform_orders = InMemoryPlatformOrdersAdapter(self.protections)
        self.ledger = InMemoryFlowLedgerAdapter()
        self.exchange.trades_on(self.order_exchange)
        # The cycle the worker runs on request, on its clock: none until a test gives one.
        self.clock = FakeClockAdapter(STARTED_AT)
        # The bell of every tenant, where the worker keeps each notification (R6.2.1).
        self.inbox: InboxStore = {}
        self.cycle_run: CycleRun = lambda _command: None
        # The adapters of the sources, the credentials the tenants gave them and what their private key opens (R6.3.1).
        self.source_systems = platform_systems()
        self.source_credentials = SourceCredentialsStore()
        self.source_vault: SourceSecretsVault = {}
        self.forecasts = InMemoryForecastRepositoryAdapter()

    def for_tenant(self, tenant_id: TenantId) -> WorkerUseCases:
        accounts = InMemoryAccountRepositoryAdapter(self.store, tenant_id)
        opener = FakeCredentialOpenerAdapter(self.vault)
        access, order_exchanges = OpenTradingAccessUseCase(accounts, opener), {HYPERLIQUID: self.order_exchange}
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, {HYPERLIQUID: self.exchange})
        protections = InMemoryProtectionRepositoryAdapter(self.protections, tenant_id)
        cancel = CancelProtectionsUseCase(access, {HYPERLIQUID: self.protection_exchange}, protections)
        closing = CloseExchangePositionUseCase(access, order_exchanges, self.orders, Slippage.default(), cancel)
        opening = OpenPositionUseCase(access, order_exchanges, self.orders, Slippage.default())
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=closing,
            run_exchange_verification=RunExchangeVerificationUseCase(
                VerificationReadings(
                    ReadAccountForVerificationUseCase(accounts, opener, {HYPERLIQUID: self.exchange}),
                    InMemoryFlowRepositoryAdapter(self.flows, tenant_id),
                ),
                procedure_orders(opening, closing, ReadMarketUseCase(access, order_exchanges)),
                self.runs,
                "dev",
                lambda: STARTED_AT,
            ),
            notify=NotifyUseCase(
                InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
                InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id),
                self.mail_servers.repository(tenant_id),
                self.outbox,
                notification_routes(tenant_id, self.channel_preferences, self.links),
                notification_inbox(tenant_id, self.inbox, self.clock),
            ),
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
                self.clock,
                self.run_cycle,
            ),
            try_source_adapter=TrySourceAdapterUseCase(
                self.source_systems,
                self.forecasts,
                OpenSourceCredentialsUseCase(
                    InMemorySourceCredentialsRepositoryAdapter(self.source_credentials, tenant_id),
                    FakeSourceSecretsOpenerAdapter(self.source_vault),
                ),
                TrialServices(ThreadPoolConcurrentCallsAdapter(), self.clock, DEFAULT_CYCLE_INTERVAL),
            ),
        )

    def run_cycle(self, command: RunCycleCommand) -> CycleRecord | None:
        """The cycle the test gives at the moment it runs, not when the use cases were built."""
        return self.cycle_run(command)

    def saved_account(self, tenant_id: TenantId = TENANT) -> Account:
        credentials = new_credentials()
        self.exchange.accept(credentials, Decimal("250.5"))
        account = an_account(tenant_id, credentials=credentials)
        sealed = account.with_credentials(
            FakeCredentialSealerAdapter(tenant_id, self.vault).seal(account.id, credentials)
        )
        self.store.accounts.append(sealed)
        return sealed
