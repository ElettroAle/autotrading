import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass, field

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.libsodium.opener import InvalidPrivateCredentialsKeyError, private_key_of
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError, public_key_of

DEFAULT_KEY_VERSION = 1
KEY_VERSION = "CREDENTIALS_KEY_VERSION"


@dataclass(frozen=True, slots=True)
class _SodiumSealingSettings:
    public_key: bytes = field(repr=False)
    key_version: int


@dataclass(frozen=True, slots=True)
class _SodiumOpeningSettings:
    private_keys: Mapping[int, bytes] = field(repr=False)


def _sealing_settings_of(source: ConfigurationSource) -> _SodiumSealingSettings:
    """The API receives only the public key: it can seal credentials, never open them (ADR 0007)."""
    try:
        public_key = base64.b64decode(source.secret("CREDENTIALS_PUBLIC_KEY"), validate=True)
    except binascii.Error as error:
        raise InvalidCredentialsKeyError from error
    public_key_of(public_key)
    return _SodiumSealingSettings(public_key, _key_version_of(source))


def _opening_settings_of(source: ConfigurationSource) -> _SodiumOpeningSettings:
    """Only the worker receives the private key (ADR 0007, ADR 0021)."""
    try:
        private_key = base64.b64decode(source.secret("CREDENTIALS_PRIVATE_KEY"), validate=True)
    except binascii.Error as error:
        raise InvalidPrivateCredentialsKeyError from error
    private_key_of(private_key)
    return _SodiumOpeningSettings({_key_version_of(source): private_key})


def _key_version_of(source: ConfigurationSource) -> int:
    text = source.optional(KEY_VERSION)
    if text is None:
        return DEFAULT_KEY_VERSION
    if not text.isdigit() or int(text) == 0:
        raise InvalidConfigurationError(KEY_VERSION)
    return int(text)
