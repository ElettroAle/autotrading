from autotrading.domain.sources.extended_indicators import EXTENDED_PARAMETERS
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.social import SOCIAL
from autotrading.domain.sources.source_list_parameter import DeclaredParameter
from autotrading.domain.sources.volumes import VOLUMES
from autotrading.domain.sources.whale import MINIMUM_USD, WHALE


def ranges(parameters: tuple[DeclaredParameter, ...]) -> list[tuple[object, ...]]:
    return [(p.key, p.label, p.default, p.minimum, p.maximum) for p in parameters]


def test_the_indicators_are_per_asset_with_the_length_of_their_series_and_the_lists_of_their_values() -> None:
    assert (INDICATORS.name, INDICATORS.per_asset, ranges(INDICATORS.parameters)) == (
        "indicatori",
        True,
        [
            ("lunghezza_serie", "lunghezza serie", 10, 1, 50),
            ("medie_periodi", "medie periodi", (20, 50), 2, 10000),
            ("rsi_periodi", "rsi periodi", (7, 14), 2, 10000),
            ("volume_relativo_candele", "volume relativo candele", (), 2, 10000),
            *ranges(EXTENDED_PARAMETERS),
            ("tendenza_giorni", "tendenza giorni", (), 1, 3650),
            ("canale_giorni", "canale giorni", (), 2, 3650),
        ],
    )


def test_the_pivots_are_per_asset_with_the_days_of_each_series_the_previous_day_by_default() -> None:
    assert (PIVOTS.name, PIVOTS.per_asset, ranges(PIVOTS.parameters)) == (
        "pivot",
        True,
        [("pivot_giorni", "pivot giorni", (1,), 1, 3650)],
    )


def test_the_forecast_is_per_asset_with_the_depth_of_its_history_its_horizons_and_the_depth_of_the_daily_one() -> None:
    assert (FORECAST.name, FORECAST.per_asset, ranges(FORECAST.parameters)) == (
        "forecast",
        True,
        [
            ("profondita_storico_giorni", "profondità storico giorni", 7, 1, 90),
            ("orizzonti_minuti", "orizzonti minuti", (15, 60), 15, 43200),
            ("profondita_lunga_giorni", "profondità lunga giorni", 365, 30, 1000),
        ],
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
    assert all(source.description for source in (INDICATORS, PIVOTS, FORECAST, SENTIMENT, NEWS, WHALE, VOLUMES, SOCIAL))
