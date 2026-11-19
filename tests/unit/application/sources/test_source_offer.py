from autotrading.application.sources.source_offer import SourceOffer
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_catalog import OfferedSource
from tests.support.source_keys import PAID, SENTIMENT, Keys

FREE = "libero"


def sentiment() -> OfferedSource:
    return Keys().sources.execute().find(SENTIMENT)


def declared(source: OfferedSource, name: str) -> SourceAdapterDeclaration:
    [adapter] = [each for each in source.adapters if each.name == name]
    return adapter


def test_an_adapter_without_configuration_is_always_activatable() -> None:
    source = sentiment()
    offer = SourceOffer(source, frozenset())

    assert (offer.configured(declared(source, FREE)), offer.missing_configuration(declared(source, FREE))) == (
        None,
        None,
    )


def test_an_adapter_the_tenant_did_not_configure_says_why_it_is_not_activatable() -> None:
    source = sentiment()
    offer = SourceOffer(source, frozenset())

    assert offer.configured(declared(source, PAID)) is False
    assert offer.missing_configuration(declared(source, PAID)) == (
        f"configura l'adapter {PAID} in Impostazioni \u203a Chiavi"
    )


def test_an_adapter_the_tenant_configured_is_activatable() -> None:
    source = sentiment()
    offer = SourceOffer(source, frozenset({PAID}))

    assert (offer.configured(declared(source, PAID)), offer.missing_configuration(declared(source, PAID))) == (
        True,
        None,
    )
