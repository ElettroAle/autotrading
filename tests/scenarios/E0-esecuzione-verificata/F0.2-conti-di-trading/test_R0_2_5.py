from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.remove_account import RemoveAccountCommand
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.keyring import Keyring
from tests.support.orders import an_executed_order
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.2-conti-di-trading/R0.2.5-rimozione-di-un-conto.feature")

LONG_BTC = Position("BTC", PositionSide.LONG, Decimal("0.001"), 2, Decimal(100000), Decimal("1.5"), None)


@dataclass
class Removal:
    platform: Platform
    keyring: Keyring
    labels: dict[str, str] = field(default_factory=dict)
    failures: list[AutotradingError] = field(default_factory=list)

    def attempt(self, user: str, account: str, *, confirmed: bool) -> None:
        command = RemoveAccountCommand(self.platform.account_named(user, account).id, confirmed=confirmed)
        try:
            self.platform.use_cases_of(user).remove_account.execute(command)
        except AutotradingError as error:
            self.failures.append(error)

    def tenant(self) -> TenantId:
        return self.platform.tenant_of("anna")


@pytest.fixture
def removal() -> Removal:
    return Removal(Platform(), Keyring())


@given(quoted('che "{user}" ha il conto "{account}" con le credenziali "{label}"'))
def user_has_account(removal: Removal, user: str, account: str, label: str) -> None:
    platform, credentials = removal.platform, removal.keyring[label]
    platform.directory.person(user).roles.add("Utente")
    platform.hyperliquid.accept(credentials)
    platform.register_account(user, registration(account, HYPERLIQUID, credentials))
    removal.labels[account] = label
    # The account has a history: an order executed and closed before today.
    platform.orders_of(platform.tenant_of(user)).add(an_executed_order(platform.account_named(user, account).id.value))


@given(quoted('che il conto "{account}" non ha posizioni aperte sull\'exchange'))
def account_without_positions(removal: Removal, account: str) -> None:
    credentials = removal.keyring[removal.labels[account]]
    assert removal.platform.hyperliquid.read_state(credentials).positions == ()


@given(quoted('che il conto "{account}" ha una posizione aperta su "{coin}" sull\'exchange'))
def account_with_position(removal: Removal, account: str, coin: str) -> None:
    assert coin == LONG_BTC.coin
    removal.platform.hyperliquid.open_position(removal.keyring[removal.labels[account]], LONG_BTC)


@when(quoted('"{user}" rimuove il conto "{account}"'))
def user_removes(removal: Removal, user: str, account: str) -> None:
    removal.attempt(user, account, confirmed=False)


@when(quoted('"{user}" rimuove il conto "{account}" senza confermare'))
def user_removes_without_confirming(removal: Removal, user: str, account: str) -> None:
    removal.attempt(user, account, confirmed=False)


@when(quoted('"{user}" rimuove il conto "{account}" confermando'))
def user_removes_confirming(removal: Removal, user: str, account: str) -> None:
    removal.attempt(user, account, confirmed=True)


@then(quoted('il conto "{account}" non compare più tra i conti di "{user}"'))
def account_gone(removal: Removal, account: str, user: str) -> None:
    assert removal.failures == []
    assert account not in [saved.name.value for saved in removal.platform.accounts_of(user)]


@then(quoted('il conto "{account}" resta tra i conti di "{user}"'))
def account_kept(removal: Removal, account: str, user: str) -> None:
    assert account in [saved.name.value for saved in removal.platform.accounts_of(user)]


@then(quoted('le credenziali "{label}" non sono più conservate dalla piattaforma'))
def credentials_gone(removal: Removal, label: str) -> None:
    platform, credentials = removal.platform, removal.keyring[label]
    assert not any(platform.uses_credentials(account, credentials) for account in platform.accounts.accounts)
    assert all(removed.credentials is None for removed in platform.accounts.removed)


@then(quoted('lo storico delle operazioni del conto "{account}" resta consultabile'))
def history_kept(removal: Removal, account: str) -> None:
    (removed,) = [removed for removed in removal.platform.accounts.removed if removed.name == account]
    history = [order for order in removal.platform.orders_of(removal.tenant()).orders]
    assert [order.request.account_id for order in history] == [removed.id.value]


@then(quoted('la rimozione è sospesa con il motivo "{reason}"'))
def removal_suspended(removal: Removal, reason: str) -> None:
    assert [str(failure) for failure in removal.failures] == [reason]


@then(quoted('la posizione su "{coin}" resta aperta sull\'exchange'))
def position_kept(removal: Removal, coin: str) -> None:
    credentials = removal.keyring[removal.labels["test-1"]]
    assert [position.coin for position in removal.platform.hyperliquid.read_state(credentials).positions] == [coin]
    assert removal.platform.order_exchange.sent == []
