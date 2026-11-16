from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TypedDict, cast

from sqlalchemy import Connection, Engine, RowMapping, Select, func, insert, literal, select, update

from autotrading.adapters.outbound.sqlalchemy.tables import forecasts
from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.tenancy.tenant_id import TenantId

HORIZONS = {horizon.minutes: horizon for horizon in ForecastHorizon}
EXPIRES_AT = forecasts.c.made_at + forecasts.c.horizon_minutes * literal(timedelta(minutes=1))


class _ForecastRow(TypedDict):
    asset: str
    horizon_minutes: int
    made_at: datetime
    predicted_price: Decimal
    actual_price: Decimal | None


class SqlAlchemyForecastRepositoryAdapter:
    """The forecasts of the flows of the tenant, never deleted, under row level security (R1.3.5, ADR 0042); the flows
    context reads them to measure their error (R3.6.1).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, forecast: PriceForecast) -> None:
        row = {
            "flow_id": forecast.flow_id,
            "asset": forecast.asset,
            "horizon_minutes": forecast.horizon.minutes,
            "made_at": forecast.made_at,
            "tenant_id": self._tenant_id.value,
            "last_price": forecast.last_price,
            "predicted_price": forecast.predicted_price,
            "history_days": forecast.history_days,
            "shortened": forecast.shortened,
            "actual_price": forecast.actual_price,
        }
        with self._transaction() as connection:
            connection.execute(insert(forecasts).values(row))

    def expired_without_actual(self, now: datetime) -> list[PriceForecast]:
        query = (
            select(forecasts)
            .where(forecasts.c.actual_price.is_(None), now >= EXPIRES_AT)
            .order_by(forecasts.c.made_at, forecasts.c.asset, forecasts.c.horizon_minutes)
        )
        with self._transaction() as connection:
            return [_forecast_of(row) for row in connection.execute(query).mappings()]

    def record_actual(self, forecast: PriceForecast) -> None:
        statement = (
            update(forecasts)
            .where(
                forecasts.c.flow_id == forecast.flow_id,
                forecasts.c.asset == forecast.asset,
                forecasts.c.horizon_minutes == forecast.horizon.minutes,
                forecasts.c.made_at == forecast.made_at,
            )
            .values(actual_price=forecast.actual_price)
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def expired_forecasts(self, flow_id: FlowId, now: datetime) -> list[EvaluatedForecast]:
        with self._transaction() as connection:
            rows = connection.execute(expired_forecasts_query(flow_id, now)).mappings()
            return [evaluated_of(row) for row in rows]

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _forecast_of(row: RowMapping) -> PriceForecast:
    actual = row["actual_price"]
    return PriceForecast(
        flow_id=row["flow_id"],
        asset=row["asset"],
        horizon=HORIZONS[row["horizon_minutes"]],
        made_at=row["made_at"],
        last_price=Decimal(row["last_price"]),
        predicted_price=Decimal(row["predicted_price"]),
        history_days=row["history_days"],
        shortened=row["shortened"],
        actual_price=None if actual is None else Decimal(actual),
    )


def expired_forecasts_query(flow_id: FlowId, now: datetime) -> Select[tuple[object, ...]]:
    return (
        select(forecasts)
        .where(forecasts.c.flow_id == flow_id.value, now >= EXPIRES_AT)
        .order_by(forecasts.c.made_at, forecasts.c.asset, forecasts.c.horizon_minutes)
    )


def evaluated_of(columns: RowMapping | Mapping[str, object]) -> EvaluatedForecast:
    row = cast("_ForecastRow", columns)
    actual = row["actual_price"]
    return EvaluatedForecast(
        asset=row["asset"],
        horizon_minutes=row["horizon_minutes"],
        expires_at=row["made_at"] + timedelta(minutes=row["horizon_minutes"]),
        predicted_price=Decimal(row["predicted_price"]),
        actual_price=None if actual is None else Decimal(actual),
    )
