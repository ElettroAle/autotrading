from decimal import Decimal

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.accounts import ADDRESS, SECRET, an_account


def test_the_summary_names_the_account_with_network_and_allocated_capital() -> None:
    account = an_account(TenantId.new())

    summary = AccountSummary.of(account, Decimal(500), ExchangeNetwork.TEST, "USDC")

    assert summary == AccountSummary(
        account.id, account.name, account.exchange, True, ExchangeNetwork.TEST, Decimal(500), "USDC"
    )
    assert ADDRESS not in repr(summary)
    assert SECRET not in repr(summary)


def test_the_summary_of_an_account_without_a_sealed_text_says_credentials_are_missing() -> None:
    account = an_account(TenantId.new(), sealed=SealedCredentials(1, b""))

    assert not AccountSummary.of(account, Decimal(0), ExchangeNetwork.REAL, "USDC").has_credentials
