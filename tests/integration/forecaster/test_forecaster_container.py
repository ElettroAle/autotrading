"""The forecaster image against a real container: Prophet, cmdstan and the read-only filesystem together (ADR 0107).

The container comes from TEST_FORECASTER_URL (started by the pipeline from the image it just built).
"""

import math
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

pytestmark = pytest.mark.integration

START = datetime(2026, 11, 1, tzinfo=UTC)


def _url() -> str:
    return os.environ.get("TEST_FORECASTER_URL", "http://localhost:8100")


def _request(asset: str) -> dict[str, object]:
    points = [
        {"at": (START + timedelta(minutes=3 * index)).isoformat(), "price": str(100 + index / 100 + math.sin(index))}
        for index in range(3000)
    ]
    return {"asset": asset, "history_days": 7, "points": points, "horizons_minutes": [15, 60]}


def test_the_container_forecasts_both_horizons_with_prophet() -> None:
    response = httpx.post(f"{_url()}/forecast", json=_request("BTC"), timeout=120)

    assert response.status_code == 200
    forecasts = response.json()["forecasts"]
    assert [forecast["horizon_minutes"] for forecast in forecasts] == [15, 60]
    for forecast in forecasts:
        predicted = Decimal(forecast["predicted_price"])
        assert Decimal(129) < predicted < Decimal(131)
        assert Decimal(forecast["lower_price"]) <= predicted <= Decimal(forecast["upper_price"])


def test_the_container_answers_its_health() -> None:
    assert httpx.get(f"{_url()}/health", timeout=10).json() == {"status": "ok"}
