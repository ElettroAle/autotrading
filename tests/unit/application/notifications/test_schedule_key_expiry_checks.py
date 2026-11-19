from datetime import UTC, time

from autotrading.application.notifications.schedule_key_expiry_checks import (
    DAILY_CHECK_NAME,
    ScheduleKeyExpiryChecksUseCase,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.key_expiries import FakeDailyCheckSchedulerAdapter

ANNA, BRUNO = TenantId.new(), TenantId.new()


class Tenants:
    def tenant_ids(self) -> tuple[TenantId, ...]:
        return (ANNA, BRUNO)


def test_the_check_runs_every_day_at_six_in_utc_for_every_tenant() -> None:
    scheduler, checked = FakeDailyCheckSchedulerAdapter(), list[TenantId]()

    ScheduleKeyExpiryChecksUseCase(scheduler, Tenants(), checked.append).execute()
    scheduler.run_all()

    assert scheduler.checks.keys() == {DAILY_CHECK_NAME}
    assert scheduler.checks[DAILY_CHECK_NAME][0] == time(6, 0, tzinfo=UTC)
    assert checked == [ANNA, BRUNO]
