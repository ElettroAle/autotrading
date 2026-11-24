"""What signs the orders of an account: opened in the worker, or nothing to open without credentials (R6.3.2)."""

from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.accounts import SIMULATED, a_simulated_account
from tests.support.worker import TENANT, Worker


def test_an_account_without_credentials_is_reached_by_its_identifier_without_opening_anything() -> None:
    worker = Worker()
    account = a_simulated_account(TENANT)
    worker.store.accounts.append(account)
    opener = FakeCredentialOpenerAdapter(worker.vault)
    use_case = OpenTradingAccessUseCase(InMemoryAccountRepositoryAdapter(worker.store, TENANT), opener)

    access = use_case.execute(OpenTradingAccessCommand(account.id.value))

    assert access == TradingAccess.without_credentials(SIMULATED, account.id.value)
    assert opener.opened_accesses == []
    assert opener.register.openings == []


def test_an_account_with_credentials_is_opened() -> None:
    worker = Worker()
    account = worker.saved_account()
    opener = FakeCredentialOpenerAdapter(worker.vault)
    use_case = OpenTradingAccessUseCase(InMemoryAccountRepositoryAdapter(worker.store, TENANT), opener)

    access = use_case.execute(OpenTradingAccessCommand(account.id.value))

    assert access.account_id is None
    assert len(opener.opened_accesses) == 1
