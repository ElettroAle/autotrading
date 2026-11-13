import base64
from pathlib import Path

import pytest
from nacl.public import PrivateKey

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.libsodium.composition import (
    libsodium_opening_adapters,
    libsodium_sealing_adapters,
)
from autotrading.adapters.outbound.libsodium.opener import InvalidPrivateCredentialsKeyError
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = PrivateKey.generate()
CREDENTIALS = Credentials("0x" + "a" * 40, "0x" + "b" * 64)


def _file(tmp_path: Path, name: str, content: str) -> str:
    location = tmp_path / name
    location.write_text(content, encoding="utf-8")
    return str(location)


def _sealing(tmp_path: Path, content: str | None = None, **overrides: str) -> ConfigurationSource:
    public = content if content is not None else base64.b64encode(bytes(KEY.public_key)).decode()
    return ConfigurationSource({"CREDENTIALS_PUBLIC_KEY_FILE": _file(tmp_path, "public", public)} | overrides)


def _opening(tmp_path: Path, content: str | None = None, **overrides: str) -> ConfigurationSource:
    private = content if content is not None else base64.b64encode(bytes(KEY)).decode()
    return ConfigurationSource({"CREDENTIALS_PRIVATE_KEY_FILE": _file(tmp_path, "private", private)} | overrides)


def test_the_sealers_of_a_tenant_seal_with_the_declared_key_and_version(tmp_path: Path) -> None:
    credential_sealer, provider_key_sealer = libsodium_sealing_adapters(_sealing(tmp_path, CREDENTIALS_KEY_VERSION="3"))
    tenant_id = TenantId.new()

    sealed = credential_sealer(tenant_id).seal(AccountId.new(), CREDENTIALS)

    assert sealed.key_version == 3
    assert "key_version=3" in repr(provider_key_sealer(tenant_id))


def test_the_key_version_is_one_unless_declared(tmp_path: Path) -> None:
    credential_sealer, _ = libsodium_sealing_adapters(_sealing(tmp_path))

    assert credential_sealer(TenantId.new()).seal(AccountId.new(), CREDENTIALS).key_version == 1


@pytest.mark.parametrize("version", ["one", "0"])
def test_a_key_version_that_is_not_a_positive_number_is_an_invalid_configuration(tmp_path: Path, version: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        libsodium_sealing_adapters(_sealing(tmp_path, CREDENTIALS_KEY_VERSION=version))

    assert raised.value.name == "CREDENTIALS_KEY_VERSION"


def test_the_public_key_must_be_declared() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        libsodium_sealing_adapters(ConfigurationSource({}))

    assert raised.value.name == "CREDENTIALS_PUBLIC_KEY_FILE"


@pytest.mark.parametrize("content", ["not base64 at all!", "c2hvcnQ="], ids=["not-base64", "short-key"])
def test_a_malformed_public_key_is_refused(tmp_path: Path, content: str) -> None:
    with pytest.raises(InvalidCredentialsKeyError):
        libsodium_sealing_adapters(_sealing(tmp_path, content))


def test_the_openers_hold_the_private_key_under_its_version(tmp_path: Path) -> None:
    opener, provider_key_opener = libsodium_opening_adapters(_opening(tmp_path, CREDENTIALS_KEY_VERSION="2"))

    assert repr(opener) == "SodiumCredentialOpenerAdapter(key_versions=[2])"
    assert "2" in repr(provider_key_opener)


def test_the_private_key_must_be_declared() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        libsodium_opening_adapters(ConfigurationSource({}))

    assert raised.value.name == "CREDENTIALS_PRIVATE_KEY_FILE"


@pytest.mark.parametrize("content", ["not base64 at all!", "c2hvcnQ="], ids=["not-base64", "short-key"])
def test_a_malformed_private_key_is_refused(tmp_path: Path, content: str) -> None:
    with pytest.raises(InvalidPrivateCredentialsKeyError):
        libsodium_opening_adapters(_opening(tmp_path, content))
