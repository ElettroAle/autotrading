import pytest

from autotrading.application.sources.errors import SourceSecretsNotOpenedError
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.domain.sources.errors import (
    SourceAdapterNotConfiguredError,
)
from tests.fakes.source_credentials import (
    FakeSourceSecretsOpenerAdapter,
)
from tests.support.source_keys import PAID, Keys


def test_the_worker_opens_the_public_and_the_secret_values_together() -> None:
    keys = Keys()
    keys.configure_paid()
    declaration = keys.sources.execute().configurable_adapter(PAID).declaration

    values = OpenSourceCredentialsUseCase(keys.credentials, FakeSourceSecretsOpenerAdapter(keys.vault)).execute(
        declaration
    )

    assert values == {"account": "anna", "api_key": "K-PAID"}


def test_an_adapter_without_configuration_opens_nothing() -> None:
    keys = Keys()
    opener = FakeSourceSecretsOpenerAdapter(keys.vault)
    [offered] = [each for each in keys.sources.execute().sources if each.name == "sentiment"]

    values = OpenSourceCredentialsUseCase(keys.credentials, opener).execute(offered.adapter("libero"))

    assert (values, opener.opened) == ({}, [])


def test_credentials_missing_at_the_cycle_make_the_adapter_absent_with_the_reason() -> None:
    keys = Keys()
    declaration = keys.sources.execute().configurable_adapter(PAID).declaration

    with pytest.raises(SourceAdapterNotConfiguredError):
        OpenSourceCredentialsUseCase(keys.credentials, FakeSourceSecretsOpenerAdapter(keys.vault)).execute(declaration)


def test_secrets_sealed_for_another_tenant_are_not_opened() -> None:
    keys = Keys()
    keys.configure_paid()
    declaration = keys.sources.execute().configurable_adapter(PAID).declaration

    with pytest.raises(SourceSecretsNotOpenedError):
        OpenSourceCredentialsUseCase(keys.credentials, FakeSourceSecretsOpenerAdapter({})).execute(declaration)
