from decimal import Decimal
from uuid import UUID

import pytest

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.get_account import GetAccountCommand, GetAccountUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.accounts import ADDRESS, SECRET, an_account
from tests.support.flows import a_configuration, a_flow

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def flows() -> FlowStore:
    return FlowStore()


def get_account(store: AccountStore, flows: FlowStore, account_id: AccountId) -> AccountSummary:
    use_case = GetAccountUseCase(
        InMemoryAccountRepositoryAdapter(store, ANNA), InMemoryFlowRepositoryAdapter(flows, ANNA), "dev", "USDC"
    )
    return use_case.execute(GetAccountCommand(account_id))


def test_details_name_the_account_and_say_only_that_credentials_are_present() -> None:
    account = an_account(ANNA)

    details = AccountDetails.of(account)

    assert (details.id, details.name, details.exchange, details.has_credentials) == (
        account.id,
        account.name,
        account.exchange,
        True,
    )
    assert ADDRESS not in repr(details)
    assert SECRET not in repr(details)


def test_details_of_an_account_without_a_sealed_text_say_credentials_are_missing() -> None:
    assert not AccountDetails.of(an_account(ANNA, sealed=SealedCredentials(1, b""))).has_credentials


def test_an_account_of_the_tenant_is_found_with_network_and_allocated_capital(
    store: AccountStore, flows: FlowStore
) -> None:
    account = an_account(ANNA)
    store.accounts.append(account)
    flows.flows.append(
        a_flow(ANNA, account_id=account.id.value, configuration=a_configuration(allocated_capital=Decimal(300)))
    )

    found = get_account(store, flows, account.id)

    assert found == AccountSummary.of(account, Decimal(300), ExchangeNetwork.TEST, "USDC")


@pytest.mark.parametrize("whose", ["another tenant", "nobody"])
def test_an_account_of_another_tenant_is_as_missing_as_one_that_does_not_exist(
    store: AccountStore, flows: FlowStore, whose: str
) -> None:
    theirs = an_account(BRUNO)
    store.accounts.append(theirs)
    account_id = theirs.id if whose == "another tenant" else AccountId(UUID(int=7))

    with pytest.raises(AccountNotFoundError) as raised:
        get_account(store, flows, account_id)

    assert str(raised.value) == "non trovato"
