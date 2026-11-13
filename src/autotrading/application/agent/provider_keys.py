"""Steps shared by the use cases on provider keys."""

import logging

from autotrading.application.agent.errors import ProviderKeyNotFoundError, UnsupportedProviderError
from autotrading.application.agent.model_gateways import ModelGateways, joined_catalog
from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey

operations = logging.getLogger("autotrading.agent")


def supported_provider(gateways: ModelGateways, name: str) -> ProviderName:
    provider = ProviderName(name)
    catalog = joined_catalog(gateways)
    if not catalog.offers(provider):
        raise UnsupportedProviderError(provider, catalog.providers)
    return provider


def registered_key(keys: ProviderKeyRepositoryPort, provider: ProviderName) -> RegisteredProviderKey:
    key = keys.get(provider)
    if key is None:
        raise ProviderKeyNotFoundError(provider)
    return key
