"""Steps shared by the use cases on provider keys."""

import logging
from datetime import date

from autotrading.application.agent.errors import (
    KeyExpiryReadByAdapterError,
    ProviderKeyNotFoundError,
    UnsupportedProviderError,
)
from autotrading.application.agent.model_gateways import ModelCatalogs, joined_catalog
from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.domain.agent.key_expiry import KeyExpiry
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey

operations = logging.getLogger("autotrading.agent")


def supported_provider(catalogs: ModelCatalogs, name: str) -> ProviderName:
    provider = ProviderName(name)
    catalog = joined_catalog(catalogs)
    if not catalog.offers(provider):
        raise UnsupportedProviderError(provider, catalog.providers)
    return provider


def registered_key(keys: ProviderKeyRepositoryPort, provider: ProviderName) -> RegisteredProviderKey:
    key = keys.get(provider)
    if key is None:
        raise ProviderKeyNotFoundError(provider)
    return key


def expiry_editable(catalogs: ModelCatalogs, provider: ProviderName) -> bool:
    """The user gives the expiry of a key only when no gateway reads it for its provider (R6.2.2)."""
    return not any(catalog.reads_key_expiry(provider) for catalog in catalogs.values())


def entered_expiry(catalogs: ModelCatalogs, provider: ProviderName, expires_on: date | None) -> KeyExpiry | None:
    """The date the user gave for the key, refused when a gateway reads it; none leaves the expiry unknown."""
    if expires_on is None:
        return None
    if not expiry_editable(catalogs, provider):
        raise KeyExpiryReadByAdapterError(provider)
    return KeyExpiry.entered(expires_on)
