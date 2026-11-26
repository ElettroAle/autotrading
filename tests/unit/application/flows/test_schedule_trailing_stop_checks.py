"""The check of the stops that follow the price, kept every minute for every tenant (R5.5.1, ADR
sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

from datetime import timedelta

from autotrading.application.flows.schedule_trailing_stop_checks import (
    TRAILING_STOP_CHECK_NAME,
    ScheduleTrailingStopChecksUseCase,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.periodic_checks import FakePeriodicCheckSchedulerAdapter

ANNA, BRUNO = TenantId.new(), TenantId.new()


class Tenants:
    def tenant_ids(self) -> tuple[TenantId, ...]:
        return (ANNA, BRUNO)


def test_the_check_runs_every_minute_for_every_tenant() -> None:
    scheduler, followed = FakePeriodicCheckSchedulerAdapter(), list[TenantId]()

    ScheduleTrailingStopChecksUseCase(scheduler, Tenants(), followed.append).execute()
    scheduler.run_all()

    assert scheduler.checks.keys() == {TRAILING_STOP_CHECK_NAME}
    assert scheduler.checks[TRAILING_STOP_CHECK_NAME][0] == timedelta(minutes=1)
    assert followed == [ANNA, BRUNO]
