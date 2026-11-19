from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_parameter import SourceParameter
from autotrading.domain.sources.whale import MINIMUM_USD, WHALE


def ranges(parameters: tuple[SourceParameter, ...]) -> list[tuple[object, ...]]:
    return [(p.key, p.label, p.default, p.minimum, p.maximum) for p in parameters]


def test_the_indicators_are_per_asset_with_the_length_of_their_series() -> None:
    assert (INDICATORS.name, INDICATORS.per_asset, ranges(INDICATORS.parameters)) == (
        "indicatori",
        True,
        [("lunghezza_serie", "lunghezza serie", 10, 1, 50)],
    )


def test_the_pivots_are_per_asset_without_parameters() -> None:
    assert (PIVOTS.name, PIVOTS.per_asset, PIVOTS.parameters) == ("pivot", True, ())


def test_the_forecast_is_per_asset_with_the_depth_of_its_history() -> None:
    assert (FORECAST.name, FORECAST.per_asset, ranges(FORECAST.parameters)) == (
        "forecast",
        True,
        [("profondita_storico_giorni", "profondità storico giorni", 7, 1, 90)],
    )


def test_the_sentiment_is_one_source_of_the_whole_market_without_parameters() -> None:
    assert (SENTIMENT.name, SENTIMENT.per_asset, SENTIMENT.parameters) == ("sentiment", False, ())


def test_the_news_concern_the_whole_market_with_count_and_age() -> None:
    assert (NEWS.name, NEWS.per_asset, ranges(NEWS.parameters)) == (
        "notizie",
        False,
        [("numero_notizie", "numero notizie", 10, 1, 50), ("eta_massima_ore", "età massima ore", 24, 1, 168)],
    )


def test_the_whale_transfers_concern_the_whole_market_with_the_threshold_left_to_the_adapter() -> None:
    assert (WHALE.name, WHALE.per_asset, WHALE.parameters, MINIMUM_USD) == ("whale", False, (), "soglia_usd")


def test_no_large_transfer_is_itself_a_datum_for_the_agent() -> None:
    assert WHALE.silence_note({MINIMUM_USD: 1_000_000}) == {
        "nota": "nessun grande trasferimento nell'ultimo intervallo"
    }


def test_every_source_describes_itself() -> None:
    assert all(source.description for source in (INDICATORS, PIVOTS, FORECAST, SENTIMENT, NEWS, WHALE))
