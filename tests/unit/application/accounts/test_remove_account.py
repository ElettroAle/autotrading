from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import AccountNotFoundError, ExchangeUnavailableError
from autotrading.application.accounts.remove_account import RemoveAccountCommand, RemoveAccountUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.errors import OpenPositionsNeedConfirmationError
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter, RemovedAccount
from tests.support.accounts import an_account

TENANT = TenantId.new()
LONG_BTC = Position("BTC", PositionSide.LONG, Decimal("0.001"), 2, Decimal(100000), Decimal(0), None)


class ScriptedAccountState:
    """Answers the positions the test decides, or fails, and records which accounts were read."""

    def __init__(self) -> None:
        self.asked: list[AccountId] = []
        self.positions: tuple[Position, ...] = ()
        self.failure: Exception | None = None

    def read_state(self, account_id: AccountId) -> AccountState:
        self.asked.append(account_id)
        if self.failure is not None:
            raise self.failure
        balance = Balance(Decimal(5), "USDC")
        return AccountState(balance, balance, self.positions, datetime(2026, 1, 1, tzinfo=UTC))


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def state() -> ScriptedAccountState:
    return ScriptedAccountState()


@pytest.fixture
def account(store: AccountStore) -> Account:
    account = an_account(TENANT)
    store.accounts.append(account)
    return account


@pytest.fixture
def use_case(store: AccountStore, state: ScriptedAccountState) -> RemoveAccountUseCase:
    return RemoveAccountUseCase(InMemoryAccountRepositoryAdapter(store, TENANT), state)


def test_an_account_without_positions_is_removed_after_reading_them(
    use_case: RemoveAccountUseCase, store: AccountStore, state: ScriptedAccountState, account: Account
) -> None:
    use_case.execute(RemoveAccountCommand(account.id))

    assert state.asked == [account.id]
    assert store.accounts == []
    assert store.removed == [RemovedAccount(account.id, TENANT, account.name.value)]


def test_an_account_with_open_positions_is_kept_without_confirmation(
    use_case: RemoveAccountUseCase, store: AccountStore, state: ScriptedAccountState, account: Account
) -> None:
    state.positions = (LONG_BTC,)

    with pytest.raises(OpenPositionsNeedConfirmationError) as raised:
        use_case.execute(RemoveAccountCommand(account.id))

    assert str(raised.value) == "il conto ha posizioni aperte che resteranno sull'exchange senza gestione"
    assert (store.accounts, store.removed) == ([account], [])


def test_a_confirmed_removal_reads_nothing_and_removes_the_account(
    use_case: RemoveAccountUseCase, store: AccountStore, state: ScriptedAccountState, account: Account
) -> None:
    state.positions = (LONG_BTC,)

    use_case.execute(RemoveAccountCommand(account.id, confirmed=True))

    assert state.asked == []
    assert [removed.id for removed in store.removed] == [account.id]


def test_a_confirmed_removal_works_when_the_exchange_cannot_be_read(
    use_case: RemoveAccountUseCase, store: AccountStore, state: ScriptedAccountState, account: Account
) -> None:
    state.failure = ExchangeUnavailableError()

    use_case.execute(RemoveAccountCommand(account.id, confirmed=True))

    assert store.accounts == []


def test_without_confirmation_an_exchange_that_cannot_be_read_keeps_the_account(
    use_case: RemoveAccountUseCase, store: AccountStore, state: ScriptedAccountState, account: Account
) -> None:
    state.failure = ExchangeUnavailableError()

    with pytest.raises(ExchangeUnavailableError):
        use_case.execute(RemoveAccountCommand(account.id))

    assert store.accounts == [account]


@pytest.mark.parametrize("confirmed", [False, True])
def test_an_account_of_another_tenant_is_not_found_and_never_read(
    use_case: RemoveAccountUseCase, store: AccountStore, state: ScriptedAccountState, confirmed: bool
) -> None:
    theirs = an_account(TenantId.new())
    store.accounts.append(theirs)

    with pytest.raises(AccountNotFoundError):
        use_case.execute(RemoveAccountCommand(theirs.id, confirmed=confirmed))

    assert (store.accounts, state.asked) == ([theirs], [])


def test_an_account_already_removed_is_not_found(use_case: RemoveAccountUseCase, account: Account) -> None:
    use_case.execute(RemoveAccountCommand(account.id))

    with pytest.raises(AccountNotFoundError):
        use_case.execute(RemoveAccountCommand(account.id))


def test_the_removal_is_recorded_by_account_id_only(
    use_case: RemoveAccountUseCase, account: Account, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="autotrading.accounts"):
        use_case.execute(RemoveAccountCommand(account.id))

    (record,) = caplog.records
    assert (record.getMessage(), record.__dict__["account_id"]) == ("conto rimosso", str(account.id.value))
