"""The reconciliation of the accounts with open positions, kept every minute for every tenant (Bug 778, ADR
riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

from datetime import timedelta

from autotrading.application.flows.schedule_open_account_reconciliations import (
    OPEN_ACCOUNT_RECONCILIATION_NAME,
    ScheduleOpenAccountReconciliationsUseCase,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.periodic_checks import FakePeriodicCheckSchedulerAdapter

ANNA, BRUNO = TenantId.new(), TenantId.new()


class Tenants:
    def tenant_ids(self) -> tuple[TenantId, ...]:
        return (ANNA, BRUNO)


def test_the_reconciliation_runs_every_minute_for_every_tenant() -> None:
    scheduler, reconciled = FakePeriodicCheckSchedulerAdapter(), list[TenantId]()

    ScheduleOpenAccountReconciliationsUseCase(scheduler, Tenants(), reconciled.append).execute()
    scheduler.run_all()

    assert scheduler.checks.keys() == {OPEN_ACCOUNT_RECONCILIATION_NAME}
    assert scheduler.checks[OPEN_ACCOUNT_RECONCILIATION_NAME][0] == timedelta(minutes=1)
    assert reconciled == [ANNA, BRUNO]
