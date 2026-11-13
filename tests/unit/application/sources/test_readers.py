from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import AssetRequiredError, SourceUnavailableError
from autotrading.application.sources.forecast_asset import ForecastAssetUseCase
from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.read_forecast import ReadForecastUseCase
from autotrading.application.sources.read_news import ReadNewsUseCase
from autotrading.application.sources.read_sentiment import ReadSentimentUseCase
from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_sample import SourceValue
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter

NOW = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
FLOW = uuid4()


class FixedSentiment:
    def __init__(self, index: SentimentIndex) -> None:
        self._index = index

    def read_index(self) -> SentimentIndex:
        return self._index


class FixedNews:
    def __init__(self, items: Sequence[NewsItem]) -> None:
        self._items = items

    def read_latest(self) -> Sequence[NewsItem]:
        return self._items


def market(settings: dict[str, int] | None = None) -> SourceRequest:
    return SourceRequest(FLOW, None, settings or {}, NOW)


def test_the_sentiment_refers_to_the_update_of_the_provider() -> None:
    updated_at = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)

    values = ReadSentimentUseCase(FixedSentiment(SentimentIndex(72, "Greed", updated_at))).execute(market())

    assert values == (
        SourceValue(
            updated_at, {"valore": "72", "classificazione": "Greed", "aggiornato_alle": "2026-11-12T00:00:00+00:00"}
        ),
    )


def story(title: str, minutes_ago: int) -> NewsItem:
    return NewsItem(title, NOW - timedelta(minutes=minutes_ago), f"sintesi {title}")


def test_the_newest_stories_within_the_settings_each_refer_to_their_publication() -> None:
    news = FixedNews([story("vecchia", 120), story("ultima", 5), story("terza", 50), story("media", 30)])

    values = ReadNewsUseCase(news).execute(market({"numero_notizie": 2, "eta_massima_ore": 1}))

    assert values == (
        SourceValue(
            NOW - timedelta(minutes=5),
            {"titolo": "ultima", "pubblicata_alle": "2026-11-12T10:02:00+00:00", "sintesi": "sintesi ultima"},
        ),
        SourceValue(
            NOW - timedelta(minutes=30),
            {"titolo": "media", "pubblicata_alle": "2026-11-12T09:37:00+00:00", "sintesi": "sintesi media"},
        ),
    )


def test_no_recent_story_gives_no_value() -> None:
    values = ReadNewsUseCase(FixedNews([story("vecchia", 120)])).execute(
        market({"numero_notizie": 10, "eta_massima_ore": 1})
    )

    assert values == ()


def forecast_reader(prices: FakePriceHistoryAdapter) -> ReadForecastUseCase:
    return ReadForecastUseCase(
        ForecastAssetUseCase(prices, FakePriceForecasterAdapter(), InMemoryForecastRepositoryAdapter())
    )


def test_the_forecast_refers_to_the_instant_it_is_made() -> None:
    prices = FakePriceHistoryAdapter(prices={"BTC": Decimal(100)})

    values = forecast_reader(prices).execute(SourceRequest(FLOW, "BTC", {"profondita_storico_giorni": 5}, NOW))

    assert values == (
        SourceValue(
            NOW,
            {
                "prezzo_attuale": "100",
                "profondita_storico_giorni": "5",
                "prezzo_previsto_15 minuti": "100.15",
                "variazione_percentuale_15 minuti": "0.15",
                "prezzo_previsto_1 ora": "100.60",
                "variazione_percentuale_1 ora": "0.60",
            },
        ),
    )
    assert prices.requests == [("BTC", 5)]


def test_a_shorter_history_is_declared_in_the_forecast() -> None:
    prices = FakePriceHistoryAdapter(available_days=3)

    (value,) = forecast_reader(prices).execute(SourceRequest(FLOW, "BTC", {"profondita_storico_giorni": 30}, NOW))

    assert value.values["profondita_storico_giorni"] == "3"
    assert value.values["storico_ridotto"] == "lo storico dell'exchange è più corto di quello richiesto"


def test_the_forecast_without_asset_is_a_defect_of_the_caller() -> None:
    with pytest.raises(AssetRequiredError, match="la fonte va interrogata per un asset") as raised:
        forecast_reader(FakePriceHistoryAdapter()).execute(market({"profondita_storico_giorni": 7}))

    assert raised.value.status_code == 500


def test_a_forecast_without_prices_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        forecast_reader(FakePriceHistoryAdapter(missing={"BTC"})).execute(
            SourceRequest(FLOW, "BTC", {"profondita_storico_giorni": 7}, NOW)
        )
