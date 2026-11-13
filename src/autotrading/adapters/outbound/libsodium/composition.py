from collections.abc import Callable
from functools import partial

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.libsodium.configuration import _opening_settings_of, _sealing_settings_of
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.domain.tenancy.tenant_id import TenantId


def libsodium_sealing_adapters(
    source: ConfigurationSource,
) -> tuple[Callable[[TenantId], SodiumCredentialSealerAdapter], Callable[[TenantId], SodiumProviderKeySealerAdapter]]:
    """The sealers of the API, each bound to the tenant of the request that receives it."""
    settings = _sealing_settings_of(source)
    return (
        partial(SodiumCredentialSealerAdapter, settings.public_key, settings.key_version),
        partial(SodiumProviderKeySealerAdapter, settings.public_key, settings.key_version),
    )


def libsodium_opening_adapters(
    source: ConfigurationSource,
) -> tuple[SodiumCredentialOpenerAdapter, SodiumProviderKeyOpenerAdapter]:
    """The openers of the worker, the only service that holds the private key."""
    settings = _opening_settings_of(source)
    return SodiumCredentialOpenerAdapter(settings.private_keys), SodiumProviderKeyOpenerAdapter(settings.private_keys)
