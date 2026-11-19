from datetime import date

from autotrading.application.accounts.key_expiry_details import KeyExpiryDetails
from autotrading.domain.accounts.key_expiry import UNKNOWN_EXPIRY, KeyExpiry, KeyExpiryReading, KeyExpiryStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.exchange import FakeExchangeAdapter
from tests.support.accounts import an_account


def test_the_details_give_the_date_its_state_on_the_day_and_whether_the_user_may_give_it() -> None:
    account = an_account(TenantId.new()).with_expiry(KeyExpiry.entered(date(2026, 12, 15)))

    details = KeyExpiryDetails.of(account, FakeExchangeAdapter(), date(2026, 12, 14))

    assert details == KeyExpiryDetails(
        KeyExpiry.entered(date(2026, 12, 15)), KeyExpiryReading(KeyExpiryStatus.EXPIRING, 1), editable=True
    )


def test_credentials_whose_exchange_reads_the_expiry_are_not_editable_and_unknown_without_a_date() -> None:
    exchange = FakeExchangeAdapter()
    exchange.reads_expiry = True

    details = KeyExpiryDetails.of(an_account(TenantId.new()), exchange, date(2026, 12, 14))

    assert details == KeyExpiryDetails(None, UNKNOWN_EXPIRY, editable=False)
