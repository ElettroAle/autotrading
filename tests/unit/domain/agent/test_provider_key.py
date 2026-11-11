import pytest

from autotrading.domain.agent.errors import ProviderKeyRequiredError, ProviderRequiredError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

KEY_TEXT = "K-SECRET-TEST"


def test_a_provider_is_named_in_lower_case_without_spaces() -> None:
    assert ProviderName("  OpenRouter ").value == "openrouter"


@pytest.mark.parametrize("name", ["", "   "])
def test_a_provider_without_name_is_refused(name: str) -> None:
    with pytest.raises(ProviderRequiredError, match=r"^fornitore obbligatorio$"):
        ProviderName(name)


def test_a_key_is_kept_without_surrounding_spaces() -> None:
    assert ProviderKey(f"  {KEY_TEXT}\n").secret == KEY_TEXT


@pytest.mark.parametrize("secret", ["", " \t"])
def test_an_empty_key_is_refused(secret: str) -> None:
    with pytest.raises(ProviderKeyRequiredError, match=r"^chiave obbligatoria$"):
        ProviderKey(secret)


def test_the_key_never_shows_in_its_representation() -> None:
    key = ProviderKey(KEY_TEXT)

    assert KEY_TEXT not in repr(key)
    assert KEY_TEXT not in str(key)
    assert KEY_TEXT not in f"{key}"


def test_the_key_is_removed_from_a_text() -> None:
    assert ProviderKey(KEY_TEXT).redact(f"invalid key {KEY_TEXT} given") == "invalid key *** given"
