"""Both Fear & Greed adapters against the shapes the two providers answer with, served in memory."""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from autotrading.adapters.outbound.alternative_me.sentiment import AlternativeMeSentimentAdapter
from autotrading.adapters.outbound.coinmarketcap.sentiment import CoinMarketCapSentimentAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.sentiment_index import SentimentIndex

ALTERNATIVE_ME_BODY = {
    "name": "Fear and Greed Index",
    "data": [{"value": "29", "value_classification": "Fear", "timestamp": "1794355200", "time_until_update": "3082"}],
    "metadata": {"error": None},
}
ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/?limit=1"
COINMARKETCAP_URL = "https://pro-api.coinmarketcap.com/public-api/v3/fear-and-greed/latest"
COINMARKETCAP_BODY = {
    "data": {"value": 26, "update_time": "2026-11-11T22:53:10.223Z", "value_classification": "Fear"},
    "status": {"error_code": "0", "error_message": ""},
}

REFUSED = "connection refused"

type Adapter = AlternativeMeSentimentAdapter | CoinMarketCapSentimentAdapter
type AdapterType = Callable[[httpx.Client], Adapter]
BOTH: list[tuple[AdapterType, str]] = [
    (AlternativeMeSentimentAdapter, "sentiment-alternative-me"),
    (CoinMarketCapSentimentAdapter, "sentiment-coinmarketcap"),
]
WITH_BODY: list[tuple[AdapterType, object]] = [
    (AlternativeMeSentimentAdapter, ALTERNATIVE_ME_BODY),
    (CoinMarketCapSentimentAdapter, COINMARKETCAP_BODY),
]


def client_answering(status: int, body: object, requested: list[str] | None = None) -> httpx.Client:
    def answer(request: httpx.Request) -> httpx.Response:
        if requested is not None:
            requested.append(str(request.url))
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(answer))


def client_answering_text(text: str) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=text)))


def unreachable_client() -> httpx.Client:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    return httpx.Client(transport=httpx.MockTransport(refuse))


def test_alternative_me_answers_with_its_latest_index() -> None:
    requested: list[str] = []
    adapter = AlternativeMeSentimentAdapter(client_answering(200, ALTERNATIVE_ME_BODY, requested))

    index = adapter.read_index()

    assert index == SentimentIndex(29, "Fear", datetime(2026, 11, 11, tzinfo=UTC))
    assert requested == [ALTERNATIVE_ME_URL]


def test_coinmarketcap_answers_with_its_latest_index_without_a_key() -> None:
    requested: list[str] = []
    seen_headers: list[httpx.Headers] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        seen_headers.append(request.headers)
        return httpx.Response(200, json=COINMARKETCAP_BODY)

    adapter = CoinMarketCapSentimentAdapter(httpx.Client(transport=httpx.MockTransport(answer)))

    index = adapter.read_index()

    assert index == SentimentIndex(26, "Fear", datetime(2026, 11, 11, 22, 53, 10, 223000, tzinfo=UTC))
    assert requested == [COINMARKETCAP_URL]
    assert "x-cmc_pro_api_key" not in seen_headers[0]


@pytest.mark.parametrize(("adapter_type", "source"), BOTH)
def test_an_unreachable_provider_is_an_unavailable_source(adapter_type: AdapterType, source: str) -> None:
    with pytest.raises(SourceUnavailableError, match=rf"^fonte non raggiungibile: {source}$") as raised:
        adapter_type(unreachable_client()).read_index()

    assert raised.value.source == source
    assert raised.value.status_code == 503


@pytest.mark.parametrize(("adapter_type", "body"), WITH_BODY)
@pytest.mark.parametrize("status", [401, 429, 500])
def test_a_refusal_of_the_provider_is_an_unavailable_source(
    adapter_type: AdapterType, body: object, status: int
) -> None:
    with pytest.raises(SourceUnavailableError):
        adapter_type(client_answering(status, body)).read_index()


@pytest.mark.parametrize(("adapter_type", "source"), BOTH)
def test_an_answer_that_is_not_json_is_an_unavailable_source(adapter_type: AdapterType, source: str) -> None:
    with pytest.raises(SourceUnavailableError, match=rf"^fonte non raggiungibile: {source}$"):
        adapter_type(client_answering_text("<html>maintenance</html>")).read_index()


@pytest.mark.parametrize(("adapter_type", "source"), BOTH)
def test_an_answer_that_is_not_an_object_is_an_unavailable_source(adapter_type: AdapterType, source: str) -> None:
    with pytest.raises(SourceUnavailableError, match=rf"^fonte non raggiungibile: {source}$"):
        adapter_type(client_answering(200, [1, 2, 3])).read_index()


@pytest.mark.parametrize(
    "body",
    [
        {"data": []},
        {"data": [{"value": "29", "value_classification": "Fear"}]},
        {"data": [{"value": "many", "value_classification": "Fear", "timestamp": "1794355200"}]},
        {"data": [{"value": "129", "value_classification": "Fear", "timestamp": "1794355200"}]},
        {"data": None},
    ],
)
def test_an_alternative_me_answer_in_another_shape_is_an_unavailable_source(body: object) -> None:
    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: sentiment-alternative-me$"):
        AlternativeMeSentimentAdapter(client_answering(200, body)).read_index()


@pytest.mark.parametrize(
    "body",
    [
        {"status": {"error_code": "0"}},
        {"data": {"value": 26, "value_classification": "Fear"}},
        {"data": {"value": 26, "update_time": "yesterday", "value_classification": "Fear"}},
        {"data": {"value": 26, "update_time": "2026-11-11T22:53:10", "value_classification": "Fear"}},
        {"data": {"value": None, "update_time": "2026-11-11T22:53:10Z", "value_classification": "Fear"}},
        {"data": "none"},
    ],
)
def test_a_coinmarketcap_answer_in_another_shape_is_an_unavailable_source(body: object) -> None:
    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: sentiment-coinmarketcap$"):
        CoinMarketCapSentimentAdapter(client_answering(200, body)).read_index()
