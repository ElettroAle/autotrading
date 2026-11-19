from datetime import date

import pytest

from autotrading.application.sources.errors import SourceSecretsNotOpenedError
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.domain.sources.key_expiry import KeyExpiry, KeyExpiryStatus
from tests.fakes.source_credentials import (
    FakeSourceSecretsOpenerAdapter,
)
from tests.support.source_keys import ACCOUNT, API_KEY, PAID, REJECTED_AT, Keys


def test_lists_only_the_adapters_that_need_configuration_not_configured_at_first() -> None:
    [summary] = Keys().listing.execute()

    assert (summary.adapter, summary.sources, summary.fields) == (PAID, ("sentiment",), (API_KEY, ACCOUNT))
    assert (summary.configured, summary.public_values, summary.registered_at) == (False, {}, None)
    assert summary.reading.status is KeyExpiryStatus.UNKNOWN


def test_the_expiry_given_with_the_credentials_is_shown_as_of_today() -> None:
    keys = Keys()

    keys.configure_paid(expires_on=date(2026, 12, 15))

    [summary] = keys.listing.execute()
    assert summary.expiry == KeyExpiry.entered(date(2026, 12, 15))
    assert (summary.reading.status, summary.reading.days_left, summary.expiry_editable) == (
        KeyExpiryStatus.EXPIRING,
        30,
        True,
    )


def test_a_refusal_of_the_provider_is_shown_until_the_credentials_are_replaced() -> None:
    keys = Keys()
    keys.configure_paid()

    keys.credentials.mark_rejected(PAID, REJECTED_AT)

    [summary] = keys.listing.execute()
    assert summary.rejected


def test_the_credentials_of_another_tenant_are_not_seen() -> None:
    bruno = Keys()
    bruno.configure_paid()

    [summary] = Keys(store=bruno.store).listing.execute()

    assert not summary.configured


def test_secrets_sealed_for_another_tenant_are_not_opened() -> None:
    keys = Keys()
    keys.configure_paid()
    declaration = keys.sources.execute().configurable_adapter(PAID).declaration

    with pytest.raises(SourceSecretsNotOpenedError):
        OpenSourceCredentialsUseCase(keys.credentials, FakeSourceSecretsOpenerAdapter({})).execute(declaration)
