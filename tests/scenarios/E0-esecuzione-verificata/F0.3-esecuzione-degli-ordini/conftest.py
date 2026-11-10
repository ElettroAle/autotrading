import pytest
from pytest_bdd import given, then

from tests.support.steps import quoted
from tests.support.trading import Trading


@pytest.fixture
def trading() -> Trading:
    return Trading()


@given(quoted('che il conto "{account}" è su "{exchange}"'))
def account_on_exchange(trading: Trading, account: str, exchange: str) -> None:
    trading.add_account(account, exchange)


@then(quoted('l\'esito riporta il motivo "{reason}"'))
def outcome_reports_reason(trading: Trading, reason: str) -> None:
    assert trading.reason() == reason
