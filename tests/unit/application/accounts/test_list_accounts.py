from decimal import Decimal

import pytest

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

ANNA, BRUNO = TenantId.new(), TenantId.new()
CURRENCY = "USDC"


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def flows() -> FlowStore:
    return FlowStore()


def list_accounts(store: AccountStore, flows: FlowStore, environment: str = "dev") -> list[AccountSummary]:
    use_case = ListAccountsUseCase(
        InMemoryAccountRepositoryAdapter(store, ANNA), InMemoryFlowRepositoryAdapter(flows, ANNA), environment, CURRENCY
    )
    return use_case.execute()


def test_the_list_holds_the_accounts_of_the_tenant_only(store: AccountStore, flows: FlowStore) -> None:
    mine, theirs = an_account(ANNA, "conto-anna"), an_account(BRUNO, "conto-bruno")
    store.accounts += [mine, theirs]

    listed = list_accounts(store, flows)

    assert [summary.id for summary in listed] == [mine.id]


def test_each_account_carries_the_capital_its_flows_not_archived_hold(store: AccountStore, flows: FlowStore) -> None:
    account = an_account(ANNA, "principale")
    store.accounts.append(account)
    flows.flows += [
        a_flow(
            ANNA,
            name=name,
            status=status,
            account_id=account.id.value,
            configuration=a_configuration(allocated_capital=capital),
        )
        for name, status, capital in (
            ("alfa", FlowStatus.ACTIVE, Decimal(300)),
            ("beta", FlowStatus.STOPPED, Decimal(200)),
            ("gamma", FlowStatus.ARCHIVED, Decimal(700)),
        )
    ]

    [summary] = list_accounts(store, flows)

    assert (summary.allocated_capital, summary.currency) == (Decimal(500), CURRENCY)


@pytest.mark.parametrize(("environment", "network"), [("dev", ExchangeNetwork.TEST), ("prod", ExchangeNetwork.REAL)])
def test_each_account_carries_the_network_of_the_installation(
    store: AccountStore, flows: FlowStore, environment: str, network: ExchangeNetwork
) -> None:
    store.accounts.append(an_account(ANNA))

    [summary] = list_accounts(store, flows, environment)

    assert summary.network is network
