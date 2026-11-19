from datetime import date

import pytest

from autotrading.application.sources.configure_source_adapter import (
    ConfigureSourceAdapterCommand,
)
from autotrading.domain.sources.errors import (
    SourceAdapterNotFoundError,
    SourceAdapterWithoutConfigurationError,
    SourceConfigurationFieldRequiredError,
)
from tests.support.source_keys import PAID, REJECTED_AT, Keys


def test_configuring_an_adapter_seals_the_secrets_and_keeps_the_public_values_in_clear() -> None:
    keys = Keys()

    keys.configure_paid()

    [summary] = keys.listing.execute()
    assert (summary.configured, summary.public_values, summary.registered_at) == (
        True,
        {"account": "anna"},
        keys.store.now,
    )
    saved = keys.credentials.get(PAID)
    assert saved is not None
    assert b"K-PAID" not in saved.sealed.ciphertext
    assert "K-PAID" not in repr(summary)
    assert keys.vault[saved.sealed.ciphertext] == (keys.tenant_id, PAID, {"api_key": "K-PAID"})


def test_a_replacement_takes_the_new_secrets_and_forgets_the_refusal_and_the_old_expiry() -> None:
    keys = Keys()
    keys.configure_paid(expires_on=date(2026, 12, 15))
    keys.credentials.mark_rejected(PAID, REJECTED_AT)

    keys.configure_paid("K-NEW")

    saved = keys.credentials.get(PAID)
    assert saved is not None
    assert (saved.rejected_at, saved.expiry) == (None, None)
    assert keys.vault[saved.sealed.ciphertext][2] == {"api_key": "K-NEW"}


def test_a_declared_field_left_empty_is_refused_and_nothing_is_saved() -> None:
    keys = Keys()

    with pytest.raises(SourceConfigurationFieldRequiredError):
        keys.configure.execute(ConfigureSourceAdapterCommand(PAID, {"api_key": "K", "account": " "}))

    assert keys.credentials.get(PAID) is None


@pytest.mark.parametrize(
    ("adapter", "error"),
    [("libero", SourceAdapterWithoutConfigurationError), ("oroscopo", SourceAdapterNotFoundError)],
)
def test_only_an_adapter_that_needs_configuration_takes_credentials(adapter: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        Keys().configure.execute(ConfigureSourceAdapterCommand(adapter, {"api_key": "K"}))
