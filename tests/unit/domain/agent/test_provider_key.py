import pytest

from autotrading.domain.agent.errors import (
    ProviderKeyFieldRequiredError,
    ProviderKeyRequiredError,
    ProviderRequiredError,
    UnknownProviderKeyFieldError,
)
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD, ProviderKeyField
from autotrading.domain.agent.provider_name import ProviderName

KEY_TEXT = "K-SECRET-TEST"
BASE = "https://models.example.test"
FIELDS = (
    ProviderKeyField("api_key", "Chiave API", secret=True),
    ProviderKeyField("api_base", "Indirizzo", secret=False),
)


def test_a_provider_is_named_in_lower_case_without_spaces() -> None:
    assert ProviderName("  OpenRouter ").value == "openrouter"


@pytest.mark.parametrize("name", ["", "   "])
def test_a_provider_without_name_is_refused(name: str) -> None:
    with pytest.raises(ProviderRequiredError, match=r"^fornitore obbligatorio$"):
        ProviderName(name)


def test_a_key_keeps_each_declared_field_without_surrounding_spaces() -> None:
    key = ProviderKey.declared(FIELDS, {"api_key": f"  {KEY_TEXT}\n", "api_base": f" {BASE} "})

    assert (key.value("api_key"), key.value("api_base")) == (KEY_TEXT, BASE)


@pytest.mark.parametrize("values", [{}, {"api_key": " \t", "api_base": ""}])
def test_a_key_without_any_value_is_refused(values: dict[str, str]) -> None:
    with pytest.raises(ProviderKeyRequiredError, match=r"^chiave obbligatoria$"):
        ProviderKey.declared(FIELDS, values)


def test_a_declared_field_left_empty_is_refused_by_its_label() -> None:
    with pytest.raises(ProviderKeyFieldRequiredError, match=r"^indirizzo obbligatorio$") as raised:
        ProviderKey.declared(FIELDS, {"api_key": KEY_TEXT})

    assert raised.value.details == {"field": "api_base"}


def test_a_field_the_provider_does_not_declare_is_refused() -> None:
    with pytest.raises(UnknownProviderKeyFieldError, match=r"^campo della chiave non previsto: region$") as raised:
        ProviderKey.declared(FIELDS, {"api_key": KEY_TEXT, "api_base": BASE, "region": "eu"})

    assert raised.value.details == {"field": "region"}


def test_a_key_without_values_cannot_exist() -> None:
    with pytest.raises(ProviderKeyRequiredError):
        ProviderKey({})


def test_a_value_not_held_is_refused() -> None:
    with pytest.raises(ProviderKeyRequiredError):
        ProviderKey({"api_key": KEY_TEXT}).value("api_base")


def test_the_key_never_shows_in_its_representation() -> None:
    key = ProviderKey({"api_key": KEY_TEXT, "api_base": BASE})

    assert all(KEY_TEXT not in text and BASE not in text for text in (repr(key), str(key), f"{key}"))


def test_every_value_is_removed_from_a_text() -> None:
    key = ProviderKey({"api_key": KEY_TEXT, "api_base": BASE})

    assert key.redact(f"invalid key {KEY_TEXT} at {BASE}") == "invalid key *** at ***"


def test_the_usual_key_is_the_secret_api_key() -> None:
    assert ProviderKeyField("api_key", "Chiave API", secret=True) == API_KEY_FIELD
