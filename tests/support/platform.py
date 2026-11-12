"""The platform as the scenarios see it: the use cases of a tenant built on the fake adapters, as bootstrap does."""

from datetime import UTC, datetime
from secrets import token_hex

from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import WorkerUseCases
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand
from autotrading.application.flows.archive_flow import ArchiveFlowUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.record_manual_closing import RecordManualClosingUseCase
from autotrading.application.flows.stop_flow import StopFlowUseCase, StopPorts
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import LinkStores
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.application.verification.run_exchange_verification import RunExchangeVerificationUseCase
from autotrading.bootstrap import (
    MODEL_CATALOG,
    SOURCE_CATALOG,
    AccountActivityFromAccounts,
    AccountFlowsFromFlows,
    AccountReadingFromAccounts,
    FlowAccountsFromAccounts,
    FlowDirectoryFromFlows,
    FlowPositionsFromOrders,
    FlowSummariesFromFlows,
    ManualClosingsRecordedInFlows,
    ModelSettingsFromAgent,
    NotifiedClosedPositions,
    OrderExecutionFromOrders,
    ProviderKeyUsageFromFlows,
    SourceSettingsFromSources,
    TradingAccessFromAccounts,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.account_state import FakeAccountStateAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.cycles import InMemoryCycleHistoryAdapter, InMemoryCycleRepositoryAdapter
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_openings import InMemoryFlowOpeningsAdapter
from tests.fakes.flow_operations import InMemoryFlowOperationsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.fakes.link_code_repository import (
    InMemoryLinkCodeLookupAdapter,
    InMemoryLinkCodeRepositoryAdapter,
    LinkCodeStore,
)
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.position_closing import FakePositionClosingAdapter
from tests.fakes.provider_keys import (
    FakeProviderKeySealerAdapter,
    FakeProviderKeyVerifierAdapter,
    InMemoryProviderKeyRepositoryAdapter,
    ProviderKeyStore,
    ProviderKeyVault,
)
from tests.fakes.running_cycle import FakeRunningCycleAdapter
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.fakes.verification import FakeVerificationAdapter
from tests.fakes.verification_run_repository import InMemoryVerificationRunRepositoryAdapter
from tests.support.directory import Directory

HYPERLIQUID = "Hyperliquid"
STARTED_AT = datetime(2026, 11, 10, 11, 59, 59, tzinfo=UTC)


def new_credentials() -> Credentials:
    return Credentials(account_address=f"0x{token_hex(20)}", secret_key=f"0x{token_hex(32)}")


class Platform:
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
        self.provider_keys = ProviderKeyStore()
        self.key_vault: ProviderKeyVault = {}
        self.providers = FakeProviderKeyVerifierAdapter()
        self.flows = FlowStore()
        self.markets = {HYPERLIQUID: FakeMarketsAdapter()}
        self.model_catalog: ModelCatalog = MODEL_CATALOG
        self.link_codes: LinkCodeStore = {}
        self.chats: LinkedChatStore = {}
        self.messenger = FakeMessengerAdapter()
        self.activity_reader = FakeActivityReaderAdapter()
        # What the API reads of the accounts through the worker, and the orders the platform recorded (R1.6.1).
        self.account_activity = FakeAccountActivityAdapter()
        self.platform_orders = InMemoryPlatformOrdersAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.now = STARTED_AT
        self.running_cycles = FakeRunningCycleAdapter(lambda: len(self.order_exchange.sent))
        self.closed_positions = ClosedPositionStore()
        self.cycles = InMemoryCycleRepositoryAdapter()
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
        account_state.reachable = position_closing.reachable = verification.reachable = self.worker_reachable
        accounts = InMemoryAccountRepositoryAdapter(self.accounts, tenant_id)
        provider_keys = InMemoryProviderKeyRepositoryAdapter(self.provider_keys, tenant_id)
        flows = InMemoryFlowRepositoryAdapter(self.flows, tenant_id)
        flow_positions = FlowPositionsFromOrders(position_closing)
        closed_positions = InMemoryClosedPositionRepositoryAdapter(self.closed_positions, tenant_id)
        flow_openings = InMemoryFlowOpeningsAdapter(self.orders_of(tenant_id))
        # The API hands its notifications to the worker, which holds the bot (ADR 0070).
        notified_closings = NotifiedClosedPositions(closed_positions, flows, self.worker_for(tenant_id).notify)
        stop_ports = StopPorts(self.running_cycles, flow_positions, flow_openings, notified_closings)
        ports = TenantPorts(
            accounts=accounts,
            sealer=self.sealer_of(tenant_id),
            exchanges=self.exchanges,
            account_state=account_state,
            position_closing=ManualClosingsRecordedInFlows(
                position_closing, RecordManualClosingUseCase(flows, flow_openings, notified_closings)
            ),
            verification=verification,
            source_catalog=SOURCE_CATALOG,
            provider_keys=provider_keys,
            provider_key_sealer=FakeProviderKeySealerAdapter(tenant_id, self.key_vault),
            provider_key_verifier=self.providers,
            provider_key_usage=ProviderKeyUsageFromFlows(flows),
            model_catalog=self.model_catalog,
            flows=flows,
            flow_checks=FlowChecks(
                accounts=FlowAccountsFromAccounts(accounts, account_state),
                markets=self.markets,
                models=ModelSettingsFromAgent(self.model_catalog, provider_keys),
                sources=SourceSettingsFromSources(SOURCE_CATALOG),
            ),
            flow_positions=flow_positions,
            stop_ports=stop_ports,
            account_flows=AccountFlowsFromFlows(flows, StopFlowUseCase(flows, stop_ports), ArchiveFlowUseCase(flows)),
            account_activity=self.account_activity,
            flow_ledger=self.ledger,
            flow_operations=InMemoryFlowOperationsAdapter(
                self.ledger, lambda: [account.id.value for account in accounts.list()]
            ),
            link_codes=InMemoryLinkCodeRepositoryAdapter(self.link_codes, tenant_id),
            linked_chats=InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            clock=lambda: self.now,
            closed_positions=closed_positions,
            cycle_history=InMemoryCycleHistoryAdapter(self.cycles, self.flows, tenant_id),
            flow_directory=FlowDirectoryFromFlows(flows),
            flow_summaries=FlowSummariesFromFlows(flows, accounts, InMemoryFlowTimingAdapter(self.flows, tenant_id)),
            environment="dev",
        )
        return TenantUseCases.on(tenant_id, ports)

    def worker_for(self, tenant_id: TenantId) -> WorkerUseCases:
        """What the worker builds for a request of the API, with the opener only it holds."""
        accounts = InMemoryAccountRepositoryAdapter(self.accounts, tenant_id)
        opener = FakeCredentialOpenerAdapter(self.vault)
        access = TradingAccessFromAccounts(accounts, opener)
        order_exchanges, orders = {HYPERLIQUID: self.order_exchange}, self.orders_of(tenant_id)
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, self.exchanges)
        close_exchange_position = CloseExchangePositionUseCase(access, order_exchanges, orders, self.slippage)
        open_position = OpenPositionUseCase(access, order_exchanges, orders, self.slippage)
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=close_exchange_position,
            run_exchange_verification=RunExchangeVerificationUseCase(
                AccountReadingFromAccounts(read_exchange_state),
                OrderExecutionFromOrders(open_position, close_exchange_position),
                self.runs_of(tenant_id),
                "dev",
                lambda: STARTED_AT,
            ),
            notify=NotifyUseCase(InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id), self.messenger),
            read_account_activity=ReadAccountActivityUseCase(
                AccountActivityFromAccounts(accounts, opener, {HYPERLIQUID: self.activity_reader})
            ),
        )

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

    def orders_of(self, tenant_id: TenantId) -> InMemoryOrderRepositoryAdapter:
        return self.orders.setdefault(tenant_id, InMemoryOrderRepositoryAdapter())

    def runs_of(self, tenant_id: TenantId) -> InMemoryVerificationRunRepositoryAdapter:
        return self.runs.setdefault(tenant_id, InMemoryVerificationRunRepositoryAdapter())

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
    return RegisterAccountCommand(name, exchange, credentials.account_address, credentials.secret_key)
