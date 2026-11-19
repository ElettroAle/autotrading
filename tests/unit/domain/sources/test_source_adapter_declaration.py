import pytest

from autotrading.domain.sources.errors import InvalidSourceAdapterDeclarationError
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_parameter import SourceParameter

KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)


def a_declaration(
    name: str = "fornitore",
    configuration_fields: tuple[SourceConfigurationField, ...] = (),
    parameters: tuple[SourceParameter, ...] = (),
) -> SourceAdapterDeclaration:
    return SourceAdapterDeclaration(name, "un fornitore", parameters, configuration_fields, offers_history=False)


def test_an_adapter_without_configuration_fields_needs_no_configuration() -> None:
    assert a_declaration().needs_configuration is False


def test_an_adapter_with_configuration_fields_needs_configuration() -> None:
    assert a_declaration(configuration_fields=(KEY,)).needs_configuration is True


def test_a_configuration_field_says_whether_it_is_secret() -> None:
    assert (KEY.name, KEY.label, KEY.secret) == ("api_key", "Chiave API", True)


@pytest.mark.parametrize("name", ["", "   "])
def test_an_adapter_without_a_name_is_a_defect(name: str) -> None:
    with pytest.raises(InvalidSourceAdapterDeclarationError, match=r"^adapter della fonte senza nome$") as raised:
        a_declaration(name)

    assert raised.value.status_code == 500


def test_two_configuration_fields_with_the_same_name_are_a_defect() -> None:
    with pytest.raises(InvalidSourceAdapterDeclarationError, match=r"^campo ripetuto nell'adapter fornitore: api_key$"):
        a_declaration(configuration_fields=(KEY, KEY))
