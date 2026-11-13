import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.outbound.forecaster.price_forecast import ForecasterPriceForecastAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.price_forecast import ForecastHorizon, PricePoint, history_of

NOW = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
HISTORY = history_of([PricePoint(NOW - timedelta(minutes=3 * age), Decimal(100 + age)) for age in (2, 1, 0)], 7, NOW)
HORIZONS = (ForecastHorizon.MINUTES_15, ForecastHorizon.HOUR_1)
ANSWER = {
    "forecasts": [
        {"horizon_minutes": 15, "predicted_price": "100.25", "lower_price": "99", "upper_price": "101"},
        {"horizon_minutes": 60, "predicted_price": "101.5", "lower_price": "98", "upper_price": "104"},
    ]
}


def adapter(handler: httpx.MockTransport) -> ForecasterPriceForecastAdapter:
    return ForecasterPriceForecastAdapter(httpx.Client(base_url="http://forecaster:8000", transport=handler))


def answering(document: object, status: int = 200, requests: list[httpx.Request] | None = None) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return httpx.Response(status, json=document)

    return httpx.MockTransport(handle)


def test_the_history_is_sent_and_the_predicted_price_of_every_horizon_returned() -> None:
    requests: list[httpx.Request] = []

    predicted = adapter(answering(ANSWER, requests=requests)).predict("BTC", HISTORY, HORIZONS)

    assert predicted == {ForecastHorizon.MINUTES_15: Decimal("100.25"), ForecastHorizon.HOUR_1: Decimal("101.5")}
    assert requests[0].url.path == "/forecast"
    assert json.loads(requests[0].content) == {
        "asset": "BTC",
        "history_days": 7,
        "points": [
            {"at": "2026-11-13T09:54:00+00:00", "price": "102"},
            {"at": "2026-11-13T09:57:00+00:00", "price": "101"},
            {"at": "2026-11-13T10:00:00+00:00", "price": "100"},
        ],
        "horizons_minutes": [15, 60],
    }


@pytest.mark.parametrize(
    "transport",
    [
        answering(ANSWER, status=500),
        answering({"unexpected": []}),
        answering({"forecasts": [{"horizon_minutes": 15, "predicted_price": "not a number"}]}),
        answering({"forecasts": [{"horizon_minutes": 15, "predicted_price": "100"}]}),
        answering("not a document"),
        httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("down", request=request))),
    ],
)
def test_a_forecaster_that_does_not_answer_well_leaves_the_source_unavailable(transport: httpx.MockTransport) -> None:
    with pytest.raises(SourceUnavailableError):
        adapter(transport).predict("BTC", HISTORY, HORIZONS)
