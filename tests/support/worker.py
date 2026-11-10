"""The worker of an installation, in memory, for the tests of the internal HTTP contract (ADR 0021, ADR 0023)."""

from decimal import Decimal
from secrets import token_hex

from autotrading.adapters.inbound.api.worker import WorkerUseCases
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.bootstrap import TradingAccessFromAccounts
from autotrading.domain.accounts.account import Account
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.support.accounts import an_account
from tests.support.platform import HYPERLIQUID, new_credentials

TOKEN = token_hex(16)
TENANT = TenantId.new()


class Worker:
    """The worker of an installation: its store, its exchange and the vault only its opener reads."""

    def __init__(self) -> None:
        self.store = AccountStore()
        self.vault: SealedVault = {}
        self.exchange = FakeExchangeAdapter()
        self.order_exchange = FakeOrderExchangeAdapter()
        self.orders = InMemoryOrderRepositoryAdapter()

    def for_tenant(self, tenant_id: TenantId) -> WorkerUseCases:
        accounts = InMemoryAccountRepositoryAdapter(self.store, tenant_id)
        opener = FakeCredentialOpenerAdapter(self.vault)
        return WorkerUseCases(
            read_exchange_state=ReadExchangeStateUseCase(accounts, opener, {HYPERLIQUID: self.exchange}),
            close_exchange_position=CloseExchangePositionUseCase(
                TradingAccessFromAccounts(accounts, opener),
                {HYPERLIQUID: self.order_exchange},
                self.orders,
                Slippage.default(),
            ),
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
