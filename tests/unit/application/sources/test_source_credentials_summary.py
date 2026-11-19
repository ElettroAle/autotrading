from datetime import date

from autotrading.application.sources.ports import SourceCredentialsRegistration
from autotrading.application.sources.source_credentials_summary import EXPIRY_EDITABLE, SourceCredentialsSummary
from autotrading.domain.sources.key_expiry import KeyExpiry, KeyExpiryStatus
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_catalog import ConfigurableAdapter
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.source_keys import ACCOUNT, API_KEY, PAID, REJECTED_AT, TODAY, Keys

TENANT = TenantId.new()


def paid_adapter() -> ConfigurableAdapter:
    return Keys().sources.execute().configurable_adapter(PAID)


def registration(credentials: SourceCredentials) -> SourceCredentialsRegistration:
    return SourceCredentialsRegistration(credentials, TODAY)


def credentials(expiry: KeyExpiry | None = None) -> SourceCredentials:
    return SourceCredentials(TENANT, PAID, {"account": "anna"}, SealedSourceSecrets(1, b"sealed"), expiry)


def test_an_adapter_never_configured_shows_its_fields_and_nothing_saved() -> None:
    summary = SourceCredentialsSummary.of(paid_adapter(), None, TODAY.date())

    assert (summary.adapter, summary.sources, summary.fields) == (PAID, ("sentiment",), (API_KEY, ACCOUNT))
    assert (summary.configured, summary.public_values, summary.registered_at, summary.expiry) == (
        False,
        {},
        None,
        None,
    )
    assert (summary.rejected, summary.reading.status, summary.expiry_editable) == (
        False,
        KeyExpiryStatus.UNKNOWN,
        EXPIRY_EDITABLE,
    )


def test_configured_credentials_show_the_public_values_the_instant_and_the_expiry_of_the_day() -> None:
    expiry = KeyExpiry.entered(date(2026, 11, 20))

    summary = SourceCredentialsSummary.of(paid_adapter(), registration(credentials(expiry)), TODAY.date())

    assert (summary.configured, summary.registered_at) == (True, TODAY)
    assert dict(summary.public_values) == {"account": "anna"}
    assert (summary.expiry, summary.reading.status, summary.reading.days_left) == (
        expiry,
        KeyExpiryStatus.EXPIRING,
        5,
    )


def test_credentials_the_provider_refused_are_shown_refused() -> None:
    refused = credentials().rejected(REJECTED_AT)

    summary = SourceCredentialsSummary.of(paid_adapter(), registration(refused), TODAY.date())

    assert summary.rejected
