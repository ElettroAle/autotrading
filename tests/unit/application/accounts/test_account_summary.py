from dataclasses import replace
from datetime import date
from decimal import Decimal

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.key_expiry_details import KeyExpiryDetails
from autotrading.domain.accounts.declared_network import DeclaredNetwork
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.key_expiry import KeyExpiry, KeyExpiryReading, KeyExpiryStatus
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.accounts import ADDRESS, SECRET, an_account

TESTNET = DeclaredNetwork.of(real=False, name="testnet")
MAINNET = DeclaredNetwork.of(real=True, name="mainnet")
EXPIRY = KeyExpiryDetails(
    KeyExpiry.entered(date(2026, 12, 15)), KeyExpiryReading(KeyExpiryStatus.EXPIRING, 26), editable=True
)


def test_the_summary_names_the_account_with_network_and_allocated_capital() -> None:
    account = an_account(TenantId.new())

    summary = AccountSummary.of(account, Decimal(500), TESTNET, "USDC", EXPIRY)

    assert summary == AccountSummary(
        account.id,
        account.name,
        account.exchange,
        True,
        TESTNET,
        Decimal(500),
        "USDC",
        {"account_address": ADDRESS},
        EXPIRY,
        None,
    )
    assert SECRET not in repr(summary)


def test_the_summary_of_an_account_without_public_fields_kept_shows_none() -> None:
    account = an_account(TenantId.new())
    legacy = replace(account, exchange_account=ExchangeAccount(account.exchange_account.fingerprint))

    assert AccountSummary.of(legacy, Decimal(0), TESTNET, "USDC", EXPIRY).public_fields == {}


def test_the_summary_of_an_account_without_a_sealed_text_says_credentials_are_missing() -> None:
    account = an_account(TenantId.new(), sealed=SealedCredentials(1, b""))

    assert not AccountSummary.of(account, Decimal(0), MAINNET, "USDC", EXPIRY).has_credentials
