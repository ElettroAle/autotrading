"""R6.3.2: the simulated exchange as the API reaches it, registration, reset and isolation of the accounts, on the use
cases of a tenant built on the fake adapters with the simulated exchange in memory (ADR
exchange-simulato-con-porte-di-lettura-e-scrittura). The tables and their row level security are proven by the
integration tests of SqlAlchemySimulatedExchangeAdapter.
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.read_account_state import ReadAccountStateCommand
from autotrading.application.accounts.register_account import AccountRegistration
from autotrading.application.accounts.reset_virtual_balance import ResetVirtualBalanceCommand
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.position import Position
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.simulated_exchange import SIMULATED
from tests.support.platform import Platform
from tests.support.simulated_exchange_steps import *  # noqa: F403 - the steps of the simulated exchange, shared by the features
from tests.support.simulated_exchange_steps import book_of, register_simulated, simulated_account_of
from tests.support.steps import quoted

scenarios(
    "E6-piattaforma-e-operativita/F6.3-strumenti-di-prova/R6.3.2-exchange-simulato/api/R6.3.2-exchange-simulato.feature"
)


@dataclass
class Seen:
    registration: AccountRegistration | None = None
    states: list[AccountState] = field(default_factory=list)
    other_tenant_refused: bool = False

    def registered(self) -> AccountRegistration:
        assert self.registration is not None, "no account was registered"
        return self.registration


@pytest.fixture
def seen() -> Seen:
    return Seen()


def open_long(platform: Platform, user: str) -> None:
    account = simulated_account_of(platform, user)
    simulated = platform.simulated_exchanges(account.tenant_id)[SIMULATED]
    market = platform.order_exchange.markets["BTC"]
    order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.002"), platform.slippage)
    simulated.place_market_order(TradingAccess.without_credentials(SIMULATED, account.id.value), order, market)


def state_of(platform: Platform, user: str) -> AccountState:
    account = simulated_account_of(platform, user)
    return platform.use_cases_of(user).read_account_state.execute(ReadAccountStateCommand(account.id))


@when(quoted('"{user}" registra un conto scegliendo l\'exchange "simulato" con saldo virtuale {amount} USDC'))
def registers_simulated(platform: Platform, seen: Seen, user: str, amount: str) -> None:
    account = register_simulated(platform, user, Decimal(amount))
    seen.registration = AccountRegistration(account, state_of(platform, user).balance)


@given("che il saldo virtuale del conto è 12 USDC")
def balance_down_to_twelve(platform: Platform) -> None:
    open_long(platform, "anna")
    account = simulated_account_of(platform, "anna")
    store = platform.offers_simulated_exchange()
    tenant_id, book = store.books[account.id.value]
    store.books[account.id.value] = (tenant_id, replace(book, account=replace(book.account, balance=Decimal(12))))
    assert book_of(platform, "anna").account.balance == Decimal(12)


@given(quoted('che "{user}" ha un conto simulato con una posizione aperta'))
def simulated_with_position(platform: Platform, user: str) -> None:
    register_simulated(platform, user, Decimal(1000), name=f"simulato di {user}")
    open_long(platform, user)


@when(quoted('"{user}" azzera il conto simulato con saldo {amount} USDC'))
def resets(platform: Platform, user: str, amount: str) -> None:
    account = simulated_account_of(platform, user)
    command = ResetVirtualBalanceCommand(account.id, Decimal(amount))
    platform.use_cases_of(user).reset_virtual_balance.execute(command)


@when(quoted('"{user}" guarda le sue posizioni'))
def looks_at_positions(platform: Platform, seen: Seen, user: str) -> None:
    use_cases = platform.use_cases_of(user)
    seen.states = [
        use_cases.read_account_state.execute(ReadAccountStateCommand(account.id))
        for account in platform.accounts_of(user)
    ]
    others = (account for account in platform.accounts.accounts if account.tenant_id != platform.tenant_of(user))
    for account in others:
        try:
            use_cases.read_account_state.execute(ReadAccountStateCommand(account.id))
        except AccountNotFoundError:
            seen.other_tenant_refused = True


@then(quoted('il conto è registrato senza credenziali, sulla rete "{network}", con saldo {amount} USDC'))
def registered_without_credentials(platform: Platform, seen: Seen, network: str, amount: str) -> None:
    registration = seen.registered()
    [summary] = platform.use_cases_of("anna").list_accounts.execute()
    assert not summary.has_credentials
    assert summary.network.name == network
    assert (registration.balance.amount, registration.balance.currency) == (Decimal(amount), "USDC")


@then(quoted("il conto ha saldo {amount} USDC e nessuna posizione aperta"))
def balance_and_nothing_open(platform: Platform, amount: str) -> None:
    state = state_of(platform, "anna")
    assert state.balance.amount == Decimal(amount)
    assert state.positions == ()


@then(quoted('la posizione di "{user}" non compare'))
def position_of_other_hidden(platform: Platform, seen: Seen, user: str) -> None:
    positions: list[Position] = [position for state in seen.states for position in state.positions]
    assert positions == []
    assert seen.other_tenant_refused
    assert platform.simulated_exchanges(platform.tenant_of("anna"))[SIMULATED].open_coins() == frozenset()
    assert book_of(platform, user).account.positions != ()
