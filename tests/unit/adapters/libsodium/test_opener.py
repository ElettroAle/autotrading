import dataclasses
import json
from uuid import uuid4

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.opener import (
    InvalidPrivateCredentialsKeyError,
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.application.accounts.errors import CredentialsNotOpenedError
from autotrading.application.flows.errors import FlowCredentialsNotOpenedError
from autotrading.application.orders.errors import OrderCredentialsNotOpenedError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.accounts import an_account

CREDENTIALS = Credentials("0x1111111111111111111111111111111111111111", "0x" + "cd" * 32)
TENANT = TenantId.new()


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


@pytest.fixture
def opener(private_key: PrivateKey) -> SodiumCredentialOpenerAdapter:
    return SodiumCredentialOpenerAdapter({1: bytes(private_key)})


def sealed_account(private_key: PrivateKey, version: int = 1, tenant_id: TenantId = TENANT) -> Account:
    account = an_account(tenant_id)
    sealer = SodiumCredentialSealerAdapter(bytes(private_key.public_key), version, tenant_id)
    return account.with_credentials(sealer.seal(account.id, CREDENTIALS))


def with_plaintext(account: Account, private_key: PrivateKey, plaintext: bytes) -> Account:
    return account.with_credentials(SealedCredentials(1, SealedBox(private_key.public_key).encrypt(plaintext)))


def test_opens_what_the_sealer_sealed_for_the_same_tenant_and_account(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    assert opener.open(sealed_account(private_key)) == CREDENTIALS


def test_the_key_follows_the_version_saved_with_the_sealed_text(private_key: PrivateKey) -> None:
    newer = PrivateKey.generate()
    opener = SodiumCredentialOpenerAdapter({1: bytes(private_key), 2: bytes(newer)})

    assert opener.open(sealed_account(newer, version=2)) == CREDENTIALS


def test_credentials_copied_onto_another_account_are_refused(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    original = sealed_account(private_key)
    copy = an_account(TENANT, "test-2").with_credentials(original.credentials)

    with pytest.raises(CredentialsNotOpenedError):
        opener.open(copy)


def test_credentials_copied_onto_another_tenant_are_refused(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    original = sealed_account(private_key)
    moved = dataclasses.replace(original, tenant_id=TenantId.new())

    with pytest.raises(CredentialsNotOpenedError):
        opener.open(moved)


def test_a_version_without_a_key_is_refused(opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey) -> None:
    with pytest.raises(CredentialsNotOpenedError):
        opener.open(sealed_account(private_key, version=9))


def test_a_text_sealed_for_another_key_is_refused(opener: SodiumCredentialOpenerAdapter) -> None:
    with pytest.raises(CredentialsNotOpenedError):
        opener.open(sealed_account(PrivateKey.generate()))


@pytest.mark.parametrize(
    "plaintext",
    [b"not json", b"[1, 2]", json.dumps({"tenant_id": "x"}).encode()],
    ids=["not-json", "not-an-object", "no-match"],
)
def test_a_plaintext_of_unexpected_shape_is_refused(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey, plaintext: bytes
) -> None:
    with pytest.raises(CredentialsNotOpenedError):
        opener.open(with_plaintext(an_account(TENANT), private_key, plaintext))


def test_a_plaintext_without_the_credentials_is_refused(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    account = an_account(TENANT)
    plaintext = json.dumps({"tenant_id": str(TENANT.value), "account_id": str(account.id.value)}).encode()

    with pytest.raises(CredentialsNotOpenedError):
        opener.open(with_plaintext(account, private_key, plaintext))


def test_a_private_key_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(InvalidPrivateCredentialsKeyError):
        SodiumCredentialOpenerAdapter({1: b"short"})


def test_the_representation_never_shows_the_keys(private_key: PrivateKey) -> None:
    shown = repr(SodiumCredentialOpenerAdapter({1: bytes(private_key)}))

    assert shown == "SodiumCredentialOpenerAdapter(key_versions=[1])"


def sealed_access_of(account: Account, exchange: str = "Hyperliquid") -> SealedAccess:
    sealed = account.credentials
    return SealedAccess(account.tenant_id, account.id.value, exchange, sealed.key_version, sealed.ciphertext)


def test_opens_the_access_of_the_orders_for_the_same_tenant_and_account(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    access = opener.open_access(sealed_access_of(sealed_account(private_key)))

    assert access == TradingAccess("Hyperliquid", CREDENTIALS.account_address, CREDENTIALS.secret_key)


def test_the_access_of_another_account_is_not_opened(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    moved = dataclasses.replace(sealed_access_of(sealed_account(private_key)), account_id=uuid4())

    with pytest.raises(OrderCredentialsNotOpenedError, match=r"^credenziali del conto non leggibili$"):
        opener.open_access(moved)


def test_an_access_sealed_with_an_unknown_key_is_not_opened(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    unknown = dataclasses.replace(sealed_access_of(sealed_account(private_key)), key_version=9)

    with pytest.raises(OrderCredentialsNotOpenedError):
        opener.open_access(unknown)


def sealed_address_of(account: Account) -> SealedAddress:
    sealed = account.credentials
    return SealedAddress(
        account.tenant_id, account.id.value, account.exchange.value, sealed.key_version, sealed.ciphertext
    )


def test_opens_only_the_address_for_the_flows_of_the_same_tenant_and_account(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    assert opener.open_address(sealed_address_of(sealed_account(private_key))) == CREDENTIALS.account_address


def test_the_address_of_another_account_is_not_opened(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    moved = dataclasses.replace(sealed_address_of(sealed_account(private_key)), account_id=uuid4())

    with pytest.raises(FlowCredentialsNotOpenedError, match=r"^credenziali del conto non leggibili$"):
        opener.open_address(moved)


def test_an_address_sealed_with_an_unknown_key_is_not_opened(
    opener: SodiumCredentialOpenerAdapter, private_key: PrivateKey
) -> None:
    unknown = dataclasses.replace(sealed_address_of(sealed_account(private_key)), key_version=9)

    with pytest.raises(FlowCredentialsNotOpenedError):
        opener.open_address(unknown)
