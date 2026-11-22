"""The forecasts of a flow as the flows context reads them on PostgreSQL to measure their error (R3.6.1, ADR
errore-medio-della-previsione-nell-api).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.forecast_repository import SqlAlchemyForecastRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.flow import Flow
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

MADE = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)


def new_flow(database: Engine, tenant_id: TenantId | None = None) -> Flow:
    if tenant_id is None:
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        tenant_id = tenant.id
    account = an_account(tenant_id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant_id).add(account)
    flow = a_flow(tenant_id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    return flow


def record(database: Engine, flow: Flow, horizon: ForecastHorizon, actual: str | None) -> None:
    price = None if actual is None else Decimal(actual)
    forecast = PriceForecast(flow.id.value, "BTC", horizon, MADE, Decimal(60000), Decimal("60500.5"), 7, False, price)
    SqlAlchemyForecastRepositoryAdapter(database, flow.tenant_id).add(forecast)


def test_the_expired_forecasts_of_the_flow_read_with_their_actual_price(database: Engine) -> None:
    flow = new_flow(database)
    record(database, flow, ForecastHorizon(15), "60000")
    record(database, flow, ForecastHorizon(60), None)
    repository = SqlAlchemyForecastRepositoryAdapter(database, flow.tenant_id)

    expired = repository.expired_forecasts(flow.id, MADE + timedelta(minutes=30))

    assert expired == [
        EvaluatedForecast("BTC", 15, MADE + timedelta(minutes=15), Decimal("60500.5"), Decimal(60000)),
    ]
    assert [each.horizon_minutes for each in repository.expired_forecasts(flow.id, MADE + timedelta(hours=1))] == [
        15,
        60,
    ]


def test_the_forecasts_of_another_flow_are_left_out(database: Engine) -> None:
    flow = new_flow(database)
    other = new_flow(database, flow.tenant_id)
    record(database, other, ForecastHorizon(15), "60000")

    repository = SqlAlchemyForecastRepositoryAdapter(database, flow.tenant_id)

    assert repository.expired_forecasts(flow.id, MADE + timedelta(days=1)) == []


def test_the_forecasts_of_a_tenant_are_invisible_to_the_others(database: Engine) -> None:
    flow, other = new_flow(database), new_flow(database)
    record(database, flow, ForecastHorizon(15), "60000")

    repository = SqlAlchemyForecastRepositoryAdapter(database, other.tenant_id)

    assert repository.expired_forecasts(flow.id, MADE + timedelta(days=1)) == []
