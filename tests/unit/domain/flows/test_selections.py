import pytest

from autotrading.domain.flows.errors import (
    RepeatedSourceAdapterError,
    SourceAdapterRequiredError,
    SourceNotSelectedError,
    SourceWeightOutOfRangeError,
)
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, ActiveSource, AdapterSelection, SourceSelection

ALTERNATIVE_ME = AdapterSelection("alternative.me", 3)
COINMARKETCAP = AdapterSelection("CoinMarketCap", 7)


def test_an_adapter_weighs_five_unless_chosen() -> None:
    assert AdapterSelection("RSS").weight == DEFAULT_WEIGHT == 5


@pytest.mark.parametrize("weight", [1, 10])
def test_an_adapter_of_a_source_weighs_from_one_to_ten(weight: int) -> None:
    assert SourceSelection("notizie", (AdapterSelection("RSS", weight),)).adapters[0].weight == weight


@pytest.mark.parametrize("weight", [0, 11])
def test_a_weight_out_of_range_is_refused_naming_the_source(weight: int) -> None:
    with pytest.raises(SourceWeightOutOfRangeError, match=r"^peso fuori da 1-10: notizie$"):
        SourceSelection("notizie", (AdapterSelection("RSS", weight),))


def test_an_active_source_needs_at_least_one_adapter() -> None:
    with pytest.raises(SourceAdapterRequiredError) as raised:
        SourceSelection("sentiment", ())

    assert (str(raised.value), raised.value.source, raised.value.status_code, raised.value.details) == (
        "scegli almeno un adapter della fonte sentiment",
        "sentiment",
        422,
        {"field": "sources", "source": "sentiment"},
    )


def test_an_adapter_cannot_appear_twice_in_a_source() -> None:
    with pytest.raises(RepeatedSourceAdapterError, match=r"^adapter ripetuto nella fonte sentiment: alternative.me$"):
        SourceSelection("sentiment", (ALTERNATIVE_ME, COINMARKETCAP, AdapterSelection("alternative.me")))


def test_a_source_finds_its_adapter_by_name() -> None:
    assert SourceSelection("sentiment", (ALTERNATIVE_ME, COINMARKETCAP)).adapter("CoinMarketCap") == COINMARKETCAP


def test_an_adapter_the_source_does_not_select_is_not_active() -> None:
    with pytest.raises(SourceNotSelectedError, match=r"^fonte non attiva nel flusso: sentiment · RSS$"):
        SourceSelection("sentiment", (ALTERNATIVE_ME,)).adapter("RSS")


def test_every_adapter_of_a_source_is_an_active_source_of_the_flow_in_its_order() -> None:
    selection = SourceSelection("sentiment", (ALTERNATIVE_ME, COINMARKETCAP))

    assert selection.active == (ActiveSource("sentiment", "alternative.me"), ActiveSource("sentiment", "CoinMarketCap"))


def test_an_active_source_is_named_by_the_source_and_its_adapter() -> None:
    assert ActiveSource("sentiment", "alternative.me").label == "sentiment · alternative.me"
