from dataclasses import dataclass, replace

from autotrading.domain.agent.key_expiry import KeyExpiry
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


@dataclass(frozen=True, slots=True)
class RegisteredProviderKey(TenantOwned):
    """The key a tenant registered for a provider: at most one per provider, readable only by the worker."""

    tenant_id: TenantId
    provider: ProviderName
    sealed: SealedProviderKey
    # None while the expiry of the key is unknown (R6.2.2).
    expiry: KeyExpiry | None = None

    def with_expiry(self, expiry: KeyExpiry | None) -> RegisteredProviderKey:
        """The day the key stops working, given by the user or read by the adapter of the catalog (R6.2.2)."""
        return replace(self, expiry=expiry)
