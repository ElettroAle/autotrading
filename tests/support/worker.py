"""The worker of an installation, in memory, for the tests of the internal HTTP contract (ADR 0021, ADR 0023)."""

from datetime import UTC, datetime
from decimal import Decimal
from secrets import token_hex

from autotrading.adapters.inbound.api.worker import WorkerUseCases
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.verification.read_account_for_verification import ReadAccountForVerificationUseCase
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.bootstrap import (
    OrderExecutionFromOrders,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.verification_run_repository import InMemoryVerificationRunRepositoryAdapter
from tests.support.accounts import an_account
from tests.support.platform import HYPERLIQUID, new_credentials

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
        self.activity_reader = FakeActivityReaderAdapter()
        self.exchange.trades_on(self.order_exchange)

    def for_tenant(self, tenant_id: TenantId) -> WorkerUseCases:
        accounts = InMemoryAccountRepositoryAdapter(self.store, tenant_id)
        opener = FakeCredentialOpenerAdapter(self.vault)
        access, order_exchanges = OpenTradingAccessUseCase(accounts, opener), {HYPERLIQUID: self.order_exchange}
        read_exchange_state = ReadExchangeStateUseCase(accounts, opener, {HYPERLIQUID: self.exchange})
        closing = CloseExchangePositionUseCase(access, order_exchanges, self.orders, Slippage.default())
        opening = OpenPositionUseCase(access, order_exchanges, self.orders, Slippage.default())
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=closing,
            run_exchange_verification=RunExchangeVerificationUseCase(
                VerificationReadings(
                    ReadAccountForVerificationUseCase(accounts, opener, {HYPERLIQUID: self.exchange}),
                    InMemoryFlowRepositoryAdapter(self.flows, tenant_id),
                ),
                OrderExecutionFromOrders(opening, closing, ReadMarketUseCase(access, order_exchanges)),
                self.runs,
                "dev",
                lambda: STARTED_AT,
            ),
            notify=NotifyUseCase(InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id), self.messenger),
            read_account_activity=ReadAccountActivityUseCase(accounts, opener, {HYPERLIQUID: self.activity_reader}),
        )

    def saved_account(self, tenant_id: TenantId = TENANT) -> Account:
        credentials = new_credentials()
        self.exchange.accept(credentials, Decimal("250.5"))
        account = an_account(tenant_id, credentials=credentials)
        sealed = account.with_credentials(
            FakeCredentialSealerAdapter(tenant_id, self.vault).seal(account.id, credentials)
        )
        self.store.accounts.append(sealed)
        return sealed
