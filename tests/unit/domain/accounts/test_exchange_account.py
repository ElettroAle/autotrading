from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount

ADDRESS = "0xAbCdEf0000000000000000000000000000000001"


def test_the_same_address_in_any_case_is_the_same_exchange_account() -> None:
    first = ExchangeAccount.of(Credentials(ADDRESS, "0x01"))
    second = ExchangeAccount.of(Credentials(ADDRESS.lower(), "0x02"))

    assert first == second


def test_different_addresses_are_different_exchange_accounts() -> None:
    first = ExchangeAccount.of(Credentials(ADDRESS, "0x01"))
    second = ExchangeAccount.of(Credentials(ADDRESS.replace("1", "2"), "0x01"))

    assert first != second


def test_the_fingerprint_does_not_hold_the_address() -> None:
    fingerprint = ExchangeAccount.of(Credentials(ADDRESS, "0x01")).fingerprint

    assert ADDRESS.lower()[2:] not in fingerprint.lower()
    assert len(fingerprint) == 64
