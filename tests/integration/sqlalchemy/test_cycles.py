from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select, update

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.automatic_pause import SqlAlchemyAutomaticPauseAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.forecast_repository import SqlAlchemyForecastRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.scheduling import (
    SqlAlchemyFlowLockAdapter,
    SqlAlchemyScheduledFlowsAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tables import cycles, flows
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import Flow
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

pytestmark = pytest.mark.integration

PLANNED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def new_flow(database: Engine, minutes: int = 15) -> Flow:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    configuration = replace(a_configuration(), cycle_interval=CycleInterval(minutes))
    flow = a_flow(tenant.id, account_id=account.id.value, configuration=configuration)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return flow


def set_status(database: Engine, flow: Flow, status: str) -> None:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(flow.tenant_id.value), True)))
        connection.execute(update(flows).where(flows.c.id == flow.id.value).values(status=status))


def flow_row(database: Engine, flow: Flow) -> RowMapping:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(flow.tenant_id.value), True)))
        return connection.execute(select(flows).where(flows.c.id == flow.id.value)).mappings().one()


def cycle_rows(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(cycles)).mappings())


def test_starting_a_flow_stamps_the_anchor_of_its_cycles(database: Engine) -> None:
    flow = new_flow(database)

    set_status(database, flow, "active")

    assert flow_row(database, flow)["cycle_anchor"] is not None


def test_the_anchor_moves_to_the_resume_and_stays_while_active(database: Engine) -> None:
    flow = new_flow(database)
    set_status(database, flow, "active")
    started = flow_row(database, flow)["cycle_anchor"]
    set_status(database, flow, "paused")
    set_status(database, flow, "active")
    resumed = flow_row(database, flow)["cycle_anchor"]

    set_status(database, flow, "active")

    assert resumed > started
    assert flow_row(database, flow)["cycle_anchor"] == resumed


def test_the_scheduler_reads_the_active_flows_of_every_tenant(database: Engine) -> None:
    active, other_tenant, stopped = new_flow(database, 15), new_flow(database, 60), new_flow(database)
    set_status(database, active, "active")
    set_status(database, other_tenant, "active")

    scheduled = {
        entry.flow.flow_id: entry for entry in SqlAlchemyScheduledFlowsAdapter(database).active_of_every_tenant()
    }

    assert scheduled[active.id.value].tenant_id == active.tenant_id
    assert scheduled[active.id.value].flow.schedule.interval == timedelta(minutes=15)
    assert scheduled[active.id.value].flow.schedule.anchor == flow_row(database, active)["cycle_anchor"]
    assert scheduled[other_tenant.id.value].flow.schedule.interval == timedelta(minutes=60)
    assert stopped.id.value not in scheduled


def test_a_paused_flow_is_not_scheduled(database: Engine) -> None:
    flow = new_flow(database)
    set_status(database, flow, "active")
    set_status(database, flow, "paused")

    scheduled = [entry.flow.flow_id for entry in SqlAlchemyScheduledFlowsAdapter(database).active_of_every_tenant()]

    assert flow.id.value not in scheduled


def test_without_the_scheduler_a_transaction_sees_no_flow(database: Engine) -> None:
    flow = new_flow(database)
    set_status(database, flow, "active")

    with database.begin() as connection:
        seen = connection.execute(select(flows.c.id)).scalars().all()

    assert flow.id.value not in seen


def test_a_flow_held_by_a_cycle_is_not_held_again(database: Engine) -> None:
    lock = SqlAlchemyFlowLockAdapter(database)
    flow_id = uuid4()

    with lock.hold(flow_id) as first, lock.hold(flow_id) as second, lock.hold(uuid4()) as other:
        assert (first, second, other) == (True, False, True)

    with lock.hold(flow_id) as again:
        assert again


def test_the_automatic_pause_pauses_only_active_flows_with_the_reason(database: Engine) -> None:
    active, stopped = new_flow(database), new_flow(database)
    set_status(database, active, "active")
    reason = "credito esaurito presso openrouter"

    SqlAlchemyAutomaticPauseAdapter(database, active.tenant_id).pause([active.id], reason)
    SqlAlchemyAutomaticPauseAdapter(database, stopped.tenant_id).pause([stopped.id], reason)
    SqlAlchemyAutomaticPauseAdapter(database, active.tenant_id).pause([], reason)

    assert (flow_row(database, active)["status"], flow_row(database, active)["pause_reason"]) == ("paused", reason)
    assert (flow_row(database, stopped)["status"], flow_row(database, stopped)["pause_reason"]) == ("stopped", None)


def test_resuming_a_flow_clears_the_reason_of_the_automatic_pause(database: Engine) -> None:
    flow = new_flow(database)
    set_status(database, flow, "active")
    SqlAlchemyAutomaticPauseAdapter(database, flow.tenant_id).pause([flow.id], "chiave del fornitore non valida")

    set_status(database, flow, "active")

    assert flow_row(database, flow)["pause_reason"] is None


def test_the_automatic_pause_never_touches_another_tenant(database: Engine) -> None:
    flow, other = new_flow(database), new_flow(database)
    set_status(database, flow, "active")

    SqlAlchemyAutomaticPauseAdapter(database, other.tenant_id).pause([flow.id], "motivo")

    assert flow_row(database, flow)["status"] == "active"


def forecast_of(flow: Flow, horizon: ForecastHorizon, made_at: datetime) -> PriceForecast:
    return PriceForecast(flow.id.value, "BTC", horizon, made_at, Decimal("100.5"), Decimal("101.25"), 7, False)


def test_a_forecast_expires_with_its_horizon_and_records_its_actual_price(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyForecastRepositoryAdapter(database, flow.tenant_id)
    short = forecast_of(flow, ForecastHorizon.MINUTES_15, PLANNED)
    long = forecast_of(flow, ForecastHorizon.HOUR_1, PLANNED)
    repository.add(short)
    repository.add(long)

    expired = repository.expired_without_actual(PLANNED + timedelta(minutes=15))
    repository.record_actual(short.with_actual(Decimal(102)))

    assert expired == [short]
    assert repository.expired_without_actual(PLANNED + timedelta(hours=1)) == [long]


def test_a_forecast_reads_back_whole(database: Engine) -> None:
    flow = new_flow(database)
    repository = SqlAlchemyForecastRepositoryAdapter(database, flow.tenant_id)
    forecast = replace(forecast_of(flow, ForecastHorizon.HOUR_1, PLANNED), history_days=3, shortened=True)
    repository.add(forecast)

    assert repository.expired_without_actual(PLANNED + timedelta(days=1)) == [forecast]


def test_the_forecasts_of_a_tenant_are_invisible_to_the_others(database: Engine) -> None:
    flow, other = new_flow(database), new_flow(database)
    SqlAlchemyForecastRepositoryAdapter(database, flow.tenant_id).add(
        forecast_of(flow, ForecastHorizon.MINUTES_15, PLANNED)
    )

    assert (
        SqlAlchemyForecastRepositoryAdapter(database, other.tenant_id).expired_without_actual(
            PLANNED + timedelta(days=1)
        )
        == []
    )
