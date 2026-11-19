from autotrading.application.sources.list_source_offers import ListSourceOffersUseCase
from tests.support.source_keys import PAID, SENTIMENT, Keys


def offers_of(keys: Keys) -> ListSourceOffersUseCase:
    return ListSourceOffersUseCase(keys.sources, keys.credentials)


def test_every_source_of_the_catalog_is_offered_in_its_order() -> None:
    keys = Keys()

    offers = offers_of(keys).execute()

    assert [offer.source for offer in offers] == list(keys.sources.execute().sources)


def test_the_offers_know_the_adapters_the_tenant_configured() -> None:
    keys = Keys()
    keys.configure_paid()

    offers = offers_of(keys).execute()

    assert {offer.configured_adapters for offer in offers} == {frozenset({PAID})}


def test_the_credentials_of_another_tenant_configure_nothing() -> None:
    bruno = Keys()
    bruno.configure_paid()

    [sentiment] = [offer for offer in offers_of(Keys(store=bruno.store)).execute() if offer.source.name == SENTIMENT]

    assert sentiment.configured_adapters == frozenset()
