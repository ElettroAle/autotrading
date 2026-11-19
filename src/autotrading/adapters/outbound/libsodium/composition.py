from collections.abc import Callable
from functools import partial

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.libsodium.configuration import _opening_settings_of, _sealing_settings_of
from autotrading.adapters.outbound.libsodium.mail_password_opener import SodiumMailPasswordOpenerAdapter
from autotrading.adapters.outbound.libsodium.mail_password_sealer import SodiumMailPasswordSealerAdapter
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.libsodium.source_secrets_opener import SodiumSourceSecretsOpenerAdapter
from autotrading.adapters.outbound.libsodium.source_secrets_sealer import SodiumSourceSecretsSealerAdapter
from autotrading.domain.tenancy.tenant_id import TenantId

type SealersOfTenant = tuple[
    Callable[[TenantId], SodiumCredentialSealerAdapter],
    Callable[[TenantId], SodiumProviderKeySealerAdapter],
    Callable[[TenantId], SodiumMailPasswordSealerAdapter],
    Callable[[TenantId], SodiumSourceSecretsSealerAdapter],
]
type OpenersOfInstallation = tuple[
    SodiumCredentialOpenerAdapter,
    SodiumProviderKeyOpenerAdapter,
    Callable[[TenantId], SodiumMailPasswordOpenerAdapter],
    SodiumSourceSecretsOpenerAdapter,
]


def libsodium_sealing_adapters(source: ConfigurationSource) -> SealersOfTenant:
    """The sealers of the API, each bound to the tenant of the request that receives it."""
    settings = _sealing_settings_of(source)
    return (
        partial(SodiumCredentialSealerAdapter, settings.public_key, settings.key_version),
        partial(SodiumProviderKeySealerAdapter, settings.public_key, settings.key_version),
        partial(SodiumMailPasswordSealerAdapter, settings.public_key, settings.key_version),
        partial(SodiumSourceSecretsSealerAdapter, settings.public_key, settings.key_version),
    )


def libsodium_opening_adapters(source: ConfigurationSource) -> OpenersOfInstallation:
    """The openers of the worker, the only service that holds the private key; the password of a mail server is opened
    bound to the tenant of the message that needs it (ADR server-di-posta-per-tenant), the secrets of the adapters of
    the sources in the cycles (ADR credenziali-degli-adapter-delle-fonti)."""
    settings = _opening_settings_of(source)
    return (
        SodiumCredentialOpenerAdapter(settings.private_keys),
        SodiumProviderKeyOpenerAdapter(settings.private_keys),
        partial(SodiumMailPasswordOpenerAdapter, settings.private_keys),
        SodiumSourceSecretsOpenerAdapter(settings.private_keys),
    )
