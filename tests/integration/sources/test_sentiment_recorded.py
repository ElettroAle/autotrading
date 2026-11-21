"""Both Fear & Greed adapters against the answers of the real public endpoints, recorded live on 21 November 2026 (ADR
fonti-provate-su-risposte-registrate).

- alternative.me: https://api.alternative.me/fng/?limit=1
- CoinMarketCap: https://pro-api.coinmarketcap.com/public-api/v3/fear-and-greed/latest
- 429: the rate limit, in the error format each recording names
"""

from datetime import UTC, datetime

import pytest

from autotrading.adapters.outbound.alternative_me.sentiment import ALTERNATIVE_ME_URL, AlternativeMeSentimentAdapter
from autotrading.adapters.outbound.coinmarketcap.sentiment import COINMARKETCAP_URL, CoinMarketCapSentimentAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.sentiment_index import SentimentIndex
from tests.support.recorded_answers import RecordedHttpxService

pytestmark = pytest.mark.integration

type SentimentAdapter = type[AlternativeMeSentimentAdapter | CoinMarketCapSentimentAdapter]


def test_the_recorded_index_of_alternative_me_is_its_value_class_and_day() -> None:
    service = RecordedHttpxService("alternative_me", "fng_latest")

    index = AlternativeMeSentimentAdapter(service.client()).read_index({})

    assert index == SentimentIndex(12, "Extreme Fear", datetime(2026, 11, 21, tzinfo=UTC))


def test_the_recorded_index_of_coinmarketcap_is_its_value_class_and_update_time() -> None:
    service = RecordedHttpxService("coinmarketcap", "fear_and_greed_latest")

    index = CoinMarketCapSentimentAdapter(service.client()).read_index({})

    assert index == SentimentIndex(8, "Extreme fear", datetime(2026, 11, 21, 19, 53, 10, 23000, tzinfo=UTC))


@pytest.mark.parametrize(
    ("technology", "name", "url", "adapter_type"),
    [
        ("alternative_me", "fng_latest", ALTERNATIVE_ME_URL, AlternativeMeSentimentAdapter),
        ("coinmarketcap", "fear_and_greed_latest", COINMARKETCAP_URL, CoinMarketCapSentimentAdapter),
    ],
)
def test_the_request_is_one_get_of_the_public_endpoint_without_a_key(
    technology: str, name: str, url: str, adapter_type: SentimentAdapter
) -> None:
    service = RecordedHttpxService(technology, name)

    adapter_type(service.client()).read_index({})

    [request] = service.requests
    assert (request.method, str(request.url)) == ("GET", url)
    assert not {"authorization", "x-cmc_pro_api_key"} & set(request.headers)


@pytest.mark.parametrize(
    ("technology", "adapter_type", "source"),
    [
        ("alternative_me", AlternativeMeSentimentAdapter, "alternative.me"),
        ("coinmarketcap", CoinMarketCapSentimentAdapter, "CoinMarketCap"),
    ],
)
def test_a_rate_limit_is_a_transient_unavailability_of_the_source(
    technology: str, adapter_type: SentimentAdapter, source: str
) -> None:
    service = RecordedHttpxService(technology, error="rate_limited_429")

    with pytest.raises(SourceUnavailableError) as raised:
        adapter_type(service.client()).read_index({})

    assert (str(raised.value), raised.value.permanent) == (f"fonte non raggiungibile: {source}", False)
