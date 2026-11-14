import pytest

from autotrading.domain.accounts.errors import UndeclaredEnvironmentError, UnsupportedEnvironmentError
from autotrading.domain.accounts.installation_environment import InstallationEnvironment


@pytest.mark.parametrize(("text", "expected"), [("dev", "dev"), (" prod\n", "prod")])
def test_an_installation_is_dev_or_prod(text: str, expected: str) -> None:
    assert InstallationEnvironment.declared(text) == expected


@pytest.mark.parametrize("text", [None, "", "  "])
def test_an_installation_must_declare_its_environment(text: str | None) -> None:
    with pytest.raises(UndeclaredEnvironmentError) as raised:
        InstallationEnvironment.declared(text)

    assert str(raised.value) == "ambiente non dichiarato"


@pytest.mark.parametrize("text", ["staging", "Dev", "production"])
def test_no_other_environment_is_supported(text: str) -> None:
    with pytest.raises(UnsupportedEnvironmentError) as raised:
        InstallationEnvironment.declared(text)

    assert raised.value.environment == text
    assert str(raised.value) == "ambiente non ammesso: sono ammessi dev e prod"
