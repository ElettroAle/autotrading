from uuid import UUID

from autotrading.domain.accounts.account_id import AccountId


def test_new_identifiers_are_distinct() -> None:
    first, second = AccountId.new(), AccountId.new()

    assert first != second


def test_parses_the_text_of_an_identifier() -> None:
    text = "0b7c5d1e-1d2a-4c8e-9a51-3f3a3e9b9c10"

    assert AccountId.parse(text) == AccountId(UUID(text))
