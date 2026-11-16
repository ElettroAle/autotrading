"""The forecasts as the flows context reads them from the database (R3.6.1, ADR
errore-medio-della-previsione-nell-api).
"""

from datetime import UTC, datetime
from decimal import Decimal

from autotrading.adapters.outbound.sqlalchemy.forecast_repository import evaluated_of, expired_forecasts_query
from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.flow_id import FlowId

MADE = datetime(2026, 11, 16, 10, tzinfo=UTC)


def row(actual: Decimal | None) -> dict[str, object]:
    return {
        "asset": "BTC",
        "horizon_minutes": 60,
        "made_at": MADE,
        "predicted_price": Decimal("60500.25"),
        "actual_price": actual,
    }


def test_a_recorded_forecast_expires_with_its_horizon_beside_its_actual_price() -> None:
    assert evaluated_of(row(Decimal(60000))) == EvaluatedForecast(
        "BTC", 60, datetime(2026, 11, 16, 11, tzinfo=UTC), Decimal("60500.25"), Decimal(60000)
    )


def test_a_recorded_forecast_without_actual_price_reads_without_it() -> None:
    assert evaluated_of(row(None)).actual_price is None


def test_the_query_reads_the_forecasts_of_the_flow_expired_by_now_from_the_oldest() -> None:
    text = str(expired_forecasts_query(FlowId.new(), MADE))

    assert "forecasts.flow_id = " in text
    assert "forecasts.made_at + forecasts.horizon_minutes * " in text
    assert "<= :param_" in text
    assert text.endswith("ORDER BY forecasts.made_at, forecasts.asset, forecasts.horizon_minutes")
