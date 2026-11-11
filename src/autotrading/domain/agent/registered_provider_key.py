from dataclasses import dataclass

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
