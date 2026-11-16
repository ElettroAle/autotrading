import hashlib

from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount

ADDRESS = "0xAbCdEf0000000000000000000000000000000001"
FIELDS = (
    CredentialField("account_address", "Indirizzo del conto", secret=False),
    CredentialField("secret_key", "Chiave dell'API wallet", secret=True),
)


def credentials(address: str, secret: str) -> Credentials:
    return Credentials({"account_address": address, "secret_key": secret})


def test_the_same_address_in_any_case_is_the_same_exchange_account() -> None:
    first = ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS)
    second = ExchangeAccount.of(credentials(ADDRESS.lower(), "0x02"), FIELDS)

    assert first == second


def test_different_addresses_are_different_exchange_accounts() -> None:
    first = ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS)
    second = ExchangeAccount.of(credentials(ADDRESS.replace("1", "2"), "0x01"), FIELDS)

    assert first != second


def test_the_fingerprint_does_not_hold_the_address() -> None:
    fingerprint = ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS).fingerprint

    assert ADDRESS.lower()[2:] not in fingerprint.lower()
    assert len(fingerprint) == 64


def test_the_fingerprint_of_a_single_public_field_is_the_one_already_saved() -> None:
    # Accounts registered before the declared fields keep their fingerprint: no migration (ADR 0158).
    fingerprint = ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS).fingerprint

    assert fingerprint == hashlib.sha256(ADDRESS.lower().encode()).hexdigest()


def test_the_secret_fields_never_enter_the_fingerprint() -> None:
    assert ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS) == ExchangeAccount.of(
        credentials(ADDRESS, "0x99"), FIELDS
    )


def test_the_public_fields_are_kept_as_entered_and_the_secret_ones_never() -> None:
    exchange_account = ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS)

    assert exchange_account.public_fields == {"account_address": ADDRESS}


def test_an_account_without_public_fields_is_the_same_exchange_account_as_one_with_them() -> None:
    # Accounts registered before the public fields were kept still compare by their fingerprint (Bug 401).
    kept = ExchangeAccount.of(credentials(ADDRESS, "0x01"), FIELDS)

    assert ExchangeAccount(kept.fingerprint) == kept
    assert ExchangeAccount(kept.fingerprint).public_fields is None


def test_the_public_fields_cannot_change_after_creation() -> None:
    entered = {"account_address": ADDRESS}
    exchange_account = ExchangeAccount("digest", entered)
    entered["account_address"] = "0x02"

    assert exchange_account.public_fields == {"account_address": ADDRESS}
