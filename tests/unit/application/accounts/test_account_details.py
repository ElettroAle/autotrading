from dataclasses import replace

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.accounts import ADDRESS, SECRET, an_account


def test_the_details_show_the_public_fields_kept_never_the_secret_ones() -> None:
    details = AccountDetails.of(an_account(TenantId.new()))

    assert details.public_fields == {"account_address": ADDRESS}
    assert SECRET not in repr(details)


def test_the_details_of_an_account_without_public_fields_kept_show_none() -> None:
    account = an_account(TenantId.new())
    legacy = replace(account, exchange_account=ExchangeAccount(account.exchange_account.fingerprint))

    assert AccountDetails.of(legacy).public_fields == {}
