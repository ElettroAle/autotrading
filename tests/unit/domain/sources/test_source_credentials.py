from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from autotrading.domain.sources.errors import (
    SourceConfigurationFieldRequiredError,
    UnknownSourceConfigurationFieldError,
)
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from autotrading.domain.sources.source_credentials import SourceConfigurationValues, SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

API_KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)
ACCOUNT = SourceConfigurationField("account", "Account", secret=False)
SEALED = SealedSourceSecrets(1, b"opaque")
REJECTED_AT = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)


def credentials() -> SourceCredentials:
    return SourceCredentials(TenantId(uuid4()), "LunarCrush", {"account": "anna"}, SEALED)


def test_splits_the_values_into_public_and_secret_by_the_declared_fields() -> None:
    values = SourceConfigurationValues.declared((API_KEY, ACCOUNT), {"api_key": " K-1 ", "account": "anna"})

    assert (dict(values.public), dict(values.secrets)) == ({"account": "anna"}, {"api_key": "K-1"})


def test_refuses_a_declared_field_left_empty_naming_it() -> None:
    with pytest.raises(SourceConfigurationFieldRequiredError, match="chiave API obbligatorio") as raised:
        SourceConfigurationValues.declared((API_KEY, ACCOUNT), {"api_key": "  ", "account": "anna"})

    assert raised.value.details == {"field": "api_key"}


def test_refuses_a_field_the_adapter_does_not_declare() -> None:
    with pytest.raises(UnknownSourceConfigurationFieldError, match="campo non previsto: colore") as raised:
        SourceConfigurationValues.declared((API_KEY,), {"api_key": "K-1", "colore": "blu"})

    assert raised.value.details == {"field": "colore"}


def test_never_shows_the_secrets_in_its_representation() -> None:
    values = SourceConfigurationValues.declared((API_KEY, ACCOUNT), {"api_key": "K-SECRET", "account": "anna"})

    assert "K-SECRET" not in repr(values)
    assert "K-SECRET" not in str(values)


def test_credentials_belong_to_a_tenant() -> None:
    assert isinstance(credentials(), TenantOwned)


def test_a_rejection_keeps_the_instant_it_happened_and_the_credentials_unchanged() -> None:
    rejected = credentials().rejected(REJECTED_AT)

    assert (rejected.rejected_at, rejected.sealed, rejected.public_values) == (REJECTED_AT, SEALED, {"account": "anna"})
    assert rejected.was_rejected
    assert not credentials().was_rejected


def test_the_expiry_is_given_or_forgotten() -> None:
    expiry = KeyExpiry.entered(date(2026, 12, 15))

    dated = credentials().with_expiry(expiry)

    assert dated.expiry == expiry
    assert dated.with_expiry(None).expiry is None


def test_the_public_values_cannot_be_changed_from_outside() -> None:
    public = {"account": "anna"}
    saved = SourceCredentials(TenantId(uuid4()), "LunarCrush", public, SEALED)

    public["account"] = "bruno"

    assert saved.public_values == {"account": "anna"}
