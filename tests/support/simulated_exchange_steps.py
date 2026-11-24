"""The steps of the simulated exchange the api and worker features of R6.3.2 share: the accounts of a tenant opened on
it through the registration, as the API registers them, on the store every adapter of the platform reads.
"""

from decimal import Decimal

import pytest
from pytest_bdd import given

from autotrading.application.accounts.register_account import RegisterAccountCommand
from autotrading.domain.accounts.account import Account
from autotrading.domain.orders.simulation.simulated_book import SimulatedBook
from tests.fakes.simulated_exchange import SIMULATED
from tests.support.platform import Platform
from tests.support.steps import quoted


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.offers_simulated_exchange()
    return platform


def register_simulated(platform: Platform, user: str, balance: Decimal, name: str = "prova") -> Account:
    command = RegisterAccountCommand(name, SIMULATED, {}, virtual_balance=balance)
    return platform.register_account(user, command).account


def simulated_account_of(platform: Platform, user: str) -> Account:
    return next(account for account in platform.accounts_of(user) if account.exchange.value == SIMULATED)


def book_of(platform: Platform, user: str) -> SimulatedBook:
    account = simulated_account_of(platform, user)
    return platform.simulated_exchanges(account.tenant_id)[SIMULATED].book_of(account.id.value)


@given(quoted('che "{user}" ha registrato un conto "simulato" con saldo virtuale {amount} USDC'))
def registered_simulated_account(platform: Platform, user: str, amount: str) -> None:
    register_simulated(platform, user, Decimal(amount))
