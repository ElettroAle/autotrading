"""The account of a flow: its exchange from the accounts of the tenant, its balance read now (R0.2.2, ADR 0087)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.flow_account import read_flow_account
from autotrading.application.flows.ports import FlowAccount, FlowAccountPorts
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.account_state import FakeAccountStateAdapter
from tests.support.flows import account_id_of
from tests.support.platform import Platform


class Accounts:
    def __init__(self) -> None:
        self.platform = Platform()
        self.tenant_id = self.platform.tenant_of("anna")
        self.state = FakeAccountStateAdapter(lambda: self.platform.worker_for(self.tenant_id).read_exchange_state)
        directory = InMemoryAccountRepositoryAdapter(self.platform.accounts, self.tenant_id)
        self.ports = FlowAccountPorts(directory, self.state)


def test_the_account_of_a_flow_carries_its_exchange_and_the_balance_read_now() -> None:
    accounts = Accounts()
    account_id = account_id_of(accounts.platform, "anna", balance=Decimal("750.25"))

    assert read_flow_account(accounts.ports, account_id) == FlowAccount("Hyperliquid", Decimal("750.25"), "USDC")


def test_an_account_the_tenant_does_not_have_is_not_found_before_any_balance_is_read() -> None:
    accounts = Accounts()
    other = account_id_of(accounts.platform, "bruno")
    accounts.state.reachable = False

    for account_id in (uuid4(), other):
        with pytest.raises(FlowAccountNotFoundError, match=r"^conto non trovato$"):
            read_flow_account(accounts.ports, account_id)


def test_a_balance_that_cannot_be_read_makes_the_exchange_unavailable() -> None:
    accounts = Accounts()
    account_id = account_id_of(accounts.platform, "anna")
    accounts.state.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        read_flow_account(accounts.ports, account_id)
