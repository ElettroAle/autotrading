from collections.abc import Callable

from autotrading.application.notifications.ports import DailyCheckSchedulerPort, KeyExpiryTenantsPort
from autotrading.domain.notifications.expiring_key import DAILY_CHECK_AT
from autotrading.domain.tenancy.tenant_id import TenantId

DAILY_CHECK_NAME = "scadenze-delle-chiavi"


class ScheduleKeyExpiryChecksUseCase:
    """Checks the expiries of the keys of every tenant when the worker starts, then every day at 06:00 UTC (R6.2.2,
    ADR controllo-giornaliero-delle-scadenze): the check of one tenant runs on the ports bound to it.
    """

    def __init__(
        self,
        scheduler: DailyCheckSchedulerPort,
        tenants: KeyExpiryTenantsPort,
        check_of: Callable[[TenantId], None],
    ) -> None:
        self._scheduler = scheduler
        self._tenants = tenants
        self._check_of = check_of

    def execute(self) -> None:
        self._scheduler.keep_daily(DAILY_CHECK_NAME, DAILY_CHECK_AT, self._check_every_tenant)

    def _check_every_tenant(self) -> None:
        for tenant_id in self._tenants.tenant_ids():
            self._check_of(tenant_id)
