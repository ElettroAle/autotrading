from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import AccountNotFoundError, VirtualBalanceNotHeldError
from autotrading.application.accounts.reset_virtual_balance import (
    ResetVirtualBalanceCommand,
    ResetVirtualBalanceUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.errors import InvalidVirtualBalanceError
from autotrading.domain.accounts.virtual_balance import VirtualBalance
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.simulated_exchange import SIMULATED, InMemorySimulatedExchangeAdapter, SimulatedExchangeStore
from tests.support.accounts import a_simulated_account, an_account
from tests.support.platform import HYPERLIQUID

TENANT = TenantId.new()
BTC = Market("BTC", max_leverage=40, size_decimals=5, mid_price=Decimal(90000), min_order_value=Decimal(10))


@pytest.fixture
def accounts() -> InMemoryAccountRepositoryAdapter:
    return InMemoryAccountRepositoryAdapter(AccountStore(), TENANT)


@pytest.fixture
def simulated() -> InMemorySimulatedExchangeAdapter:
    return InMemorySimulatedExchangeAdapter(SimulatedExchangeStore(), TENANT)


def a_registered_simulated_account(
    accounts: InMemoryAccountRepositoryAdapter, simulated: InMemorySimulatedExchangeAdapter
) -> AccountId:
    account = a_simulated_account(TENANT)
    accounts.add(account)
    simulated.open(account.id, VirtualBalance(Decimal(1000)))
    return account.id


def test_the_account_starts_again_from_the_balance_given_with_nothing_open(
    accounts: InMemoryAccountRepositoryAdapter, simulated: InMemorySimulatedExchangeAdapter
) -> None:
    account_id = a_registered_simulated_account(accounts, simulated)
    access = TradingAccess.without_credentials(SIMULATED, account_id.value)
    simulated.place_market_order(
        access, MarketOrder.opening("BTC", Direction.LONG, Decimal("0.002"), Slippage.default()), BTC
    )

    ResetVirtualBalanceUseCase(accounts, {SIMULATED: simulated}).execute(
        ResetVirtualBalanceCommand(account_id, Decimal(500))
    )

    book = simulated.book_of(account_id.value)
    assert book.account.balance == Decimal(500)
    assert book.account.positions == ()


def test_an_account_of_an_exchange_with_funds_has_no_virtual_balance_to_reset(
    accounts: InMemoryAccountRepositoryAdapter, simulated: InMemorySimulatedExchangeAdapter
) -> None:
    account = an_account(TENANT)
    accounts.add(account)

    with pytest.raises(VirtualBalanceNotHeldError):
        ResetVirtualBalanceUseCase(accounts, {SIMULATED: simulated}).execute(
            ResetVirtualBalanceCommand(account.id, Decimal(500))
        )

    assert account.exchange.value == HYPERLIQUID


def test_an_account_of_another_tenant_is_not_found(simulated: InMemorySimulatedExchangeAdapter) -> None:
    other = InMemoryAccountRepositoryAdapter(AccountStore(), TenantId.new())

    with pytest.raises(AccountNotFoundError):
        ResetVirtualBalanceUseCase(other, {SIMULATED: simulated}).execute(
            ResetVirtualBalanceCommand(AccountId.new(), Decimal(500))
        )


def test_a_balance_not_above_zero_is_refused(
    accounts: InMemoryAccountRepositoryAdapter, simulated: InMemorySimulatedExchangeAdapter
) -> None:
    account_id = a_registered_simulated_account(accounts, simulated)

    with pytest.raises(InvalidVirtualBalanceError):
        ResetVirtualBalanceUseCase(accounts, {SIMULATED: simulated}).execute(
            ResetVirtualBalanceCommand(account_id, Decimal(0))
        )

    assert simulated.book_of(account_id.value).account.balance == Decimal(1000)
