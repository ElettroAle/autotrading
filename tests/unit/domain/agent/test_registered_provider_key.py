from datetime import date

from autotrading.domain.agent.key_expiry import KeyExpiry
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


def a_key() -> RegisteredProviderKey:
    return RegisteredProviderKey(TenantId.new(), ProviderName("openrouter"), SealedProviderKey(1, b"sealed"))


def test_a_registered_key_belongs_to_a_tenant() -> None:
    assert isinstance(a_key(), TenantOwned)


def test_a_key_has_an_unknown_expiry_until_one_is_given() -> None:
    key = a_key()
    expiry = KeyExpiry.entered(date(2026, 12, 15))

    assert key.expiry is None
    assert key.with_expiry(expiry).expiry == expiry
    assert key.with_expiry(expiry).with_expiry(None).expiry is None
