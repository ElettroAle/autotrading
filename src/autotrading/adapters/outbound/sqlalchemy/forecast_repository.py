from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import Connection, Engine, RowMapping, func, insert, literal, select, update

from autotrading.adapters.outbound.sqlalchemy.tables import forecasts
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.tenancy.tenant_id import TenantId

HORIZONS = {horizon.minutes: horizon for horizon in ForecastHorizon}


class SqlAlchemyForecastRepositoryAdapter:
    """The forecasts of the flows of the tenant, never deleted, under row level security (R1.3.5, ADR 0042)."""

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
        expires_at = forecasts.c.made_at + forecasts.c.horizon_minutes * literal(timedelta(minutes=1))
        query = (
            select(forecasts)
            .where(forecasts.c.actual_price.is_(None), expires_at <= now)
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
