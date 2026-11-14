import pytest

from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import (
    CredentialFieldRequiredError,
    CredentialsRequiredError,
    UnknownCredentialFieldError,
)

ADDRESS = "0x1111111111111111111111111111111111111111"
SECRET = "0x" + "ab" * 32
FIELDS = (
    CredentialField("account_address", "Indirizzo del conto", secret=False),
    CredentialField("secret_key", "Chiave dell'API wallet", secret=True),
)


def test_keeps_each_declared_value_without_surrounding_spaces() -> None:
    credentials = Credentials.declared(FIELDS, {"account_address": f" {ADDRESS} ", "secret_key": f"{SECRET}  "})

    assert (credentials.value("account_address"), credentials.value("secret_key")) == (ADDRESS, SECRET)


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ({"account_address": ADDRESS}, "chiave dell'API wallet obbligatorio"),
        ({"account_address": ADDRESS, "secret_key": " "}, "chiave dell'API wallet obbligatorio"),
        ({"secret_key": SECRET}, "indirizzo del conto obbligatorio"),
    ],
)
def test_a_declared_field_left_empty_is_refused_by_its_label(values: dict[str, str], reason: str) -> None:
    with pytest.raises(CredentialFieldRequiredError) as raised:
        Credentials.declared(FIELDS, values)

    assert str(raised.value) == reason


def test_the_refusal_names_the_field_it_misses() -> None:
    with pytest.raises(CredentialFieldRequiredError) as raised:
        Credentials.declared(FIELDS, {"account_address": ADDRESS})

    assert raised.value.field == "secret_key"


def test_a_field_the_exchange_does_not_declare_is_refused() -> None:
    with pytest.raises(UnknownCredentialFieldError) as raised:
        Credentials.declared(FIELDS, {"account_address": ADDRESS, "secret_key": SECRET, "passphrase": "x"})

    assert str(raised.value) == "campo delle credenziali non previsto: passphrase"


def test_credentials_without_any_value_are_refused() -> None:
    with pytest.raises(CredentialsRequiredError) as raised:
        Credentials({})

    assert str(raised.value) == "credenziali obbligatorio"


def test_a_value_not_held_is_refused() -> None:
    with pytest.raises(CredentialsRequiredError):
        Credentials({"account_address": ADDRESS}).value("secret_key")


def test_representation_never_shows_any_value() -> None:
    credentials = Credentials({"account_address": ADDRESS, "secret_key": SECRET})

    shown = [repr(credentials), str(credentials), f"{credentials}", repr([credentials])]

    assert all(ADDRESS not in text and SECRET not in text for text in shown)
    assert repr(credentials) == "Credentials(***)"


def test_redaction_masks_every_value_whatever_its_case() -> None:
    credentials = Credentials({"account_address": ADDRESS, "secret_key": SECRET})
    text = f"wallet {ADDRESS.upper()} signed with {SECRET} refused"

    assert credentials.redact(text) == "wallet *** signed with *** refused"


def test_redaction_leaves_other_text_untouched() -> None:
    assert Credentials({"account_address": ADDRESS, "secret_key": SECRET}).redact("exchange busy") == "exchange busy"


def test_the_refusals_name_their_field_in_the_answer() -> None:
    assert CredentialFieldRequiredError("secret_key", "Chiave").details == {"field": "secret_key"}
    assert UnknownCredentialFieldError("passphrase").details == {"field": "passphrase"}


def test_credentials_with_every_declared_field_empty_are_refused_as_a_whole() -> None:
    with pytest.raises(CredentialsRequiredError) as raised:
        Credentials.declared(FIELDS, {"account_address": " ", "secret_key": ""})

    assert str(raised.value) == "credenziali obbligatorio"
