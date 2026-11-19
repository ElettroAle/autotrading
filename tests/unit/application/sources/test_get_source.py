from uuid import uuid4

import pytest

from autotrading.application.sources.get_source import GetSourceCommand, GetSourceUseCase
from autotrading.application.sources.list_source_offers import ListSourceOffersUseCase
from autotrading.domain.sources.errors import SourceNotAvailableError
from autotrading.domain.sources.news import NEWS
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.source_credentials import InMemorySourceCredentialsRepositoryAdapter, SourceCredentialsStore
from tests.support.source_keys import PAID, Keys


def offers_of(keys: Keys) -> ListSourceOffersUseCase:
    return ListSourceOffersUseCase(keys.sources, keys.credentials)


def test_reads_one_source_of_the_catalog_with_its_adapters() -> None:
    offer = GetSourceUseCase(offers_of(Keys())).execute(GetSourceCommand("notizie"))

    assert (offer.source.definition, [adapter.name for adapter in offer.source.adapters]) == (NEWS, ["RSS"])


def test_a_source_outside_the_catalog_is_not_available() -> None:
    with pytest.raises(SourceNotAvailableError):
        GetSourceUseCase(offers_of(Keys())).execute(GetSourceCommand("oroscopo"))


def test_an_adapter_not_configured_by_the_tenant_says_why_it_is_not_activatable() -> None:
    offer = GetSourceUseCase(offers_of(Keys())).execute(GetSourceCommand("sentiment"))
    paid, free = offer.source.adapter(PAID), offer.source.adapter("libero")

    assert (offer.configured(paid), offer.missing_configuration(paid)) == (
        False,
        "configura l'adapter Pagato in Impostazioni \u203a Chiavi",
    )
    assert (offer.configured(free), offer.missing_configuration(free)) == (None, None)


def test_an_adapter_configured_by_the_tenant_is_activatable() -> None:
    keys = Keys()
    keys.configure_paid()

    offer = GetSourceUseCase(offers_of(keys)).execute(GetSourceCommand("sentiment"))

    assert (offer.configured(offer.source.adapter(PAID)), offer.missing_configuration(offer.source.adapter(PAID))) == (
        True,
        None,
    )


def test_the_offers_list_every_source_with_what_the_tenant_configured() -> None:
    keys = Keys()
    keys.configure_paid()
    other = InMemorySourceCredentialsRepositoryAdapter(SourceCredentialsStore(), TenantId(uuid4()))

    mine, theirs = offers_of(keys).execute(), ListSourceOffersUseCase(keys.sources, other).execute()

    assert {offer.configured_adapters for offer in mine} == {frozenset({PAID})}
    assert {offer.configured_adapters for offer in theirs} == {frozenset()}
