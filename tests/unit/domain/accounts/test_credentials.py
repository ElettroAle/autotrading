import pytest

from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import CredentialsRequiredError

ADDRESS = "0x1111111111111111111111111111111111111111"
SECRET = "0x" + "ab" * 32


def test_keeps_address_and_secret_without_surrounding_spaces() -> None:
    credentials = Credentials(f" {ADDRESS} ", f"{SECRET}  ")

    assert (credentials.account_address, credentials.secret_key) == (ADDRESS, SECRET)


@pytest.mark.parametrize(("address", "secret"), [("", SECRET), (ADDRESS, " "), ("", "")])
def test_rejects_missing_credentials(address: str, secret: str) -> None:
    with pytest.raises(CredentialsRequiredError) as raised:
        Credentials(address, secret)

    assert str(raised.value) == "credenziali obbligatorio"


def test_representation_never_shows_address_or_secret() -> None:
    credentials = Credentials(ADDRESS, SECRET)

    shown = [repr(credentials), str(credentials), f"{credentials}", repr([credentials])]

    assert all(ADDRESS not in text and SECRET not in text for text in shown)
    assert repr(credentials) == "Credentials(***)"
