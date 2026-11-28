from collections.abc import Callable
from datetime import timedelta

from autotrading.application.flows.every_tenant import every_tenant
from autotrading.application.flows.ports import FlowTenantsPort, PeriodicCheckSchedulerPort
from autotrading.domain.tenancy.tenant_id import TenantId

TRAILING_STOP_CHECK_NAME = "stop-che-segue-il-prezzo"
# R5.5.1: the price of a watched position is checked at least once a minute, whatever the cycle of its flow.
TRAILING_STOP_CHECK_EVERY = timedelta(minutes=1)


class ScheduleTrailingStopChecksUseCase:
    """Checks the stops that follow the price of every tenant when the worker starts, then every minute (R5.5.1, ADR
    sorveglianza-del-prezzo-per-lo-stop-che-segue): the check of one tenant runs on the ports bound to it.
    """

    def __init__(
        self,
        scheduler: PeriodicCheckSchedulerPort,
        tenants: FlowTenantsPort,
        follow_of: Callable[[TenantId], None],
    ) -> None:
        self._scheduler = scheduler
        self._tenants = tenants
        self._follow_of = follow_of

    def execute(self) -> None:
        self._scheduler.keep_every(
            TRAILING_STOP_CHECK_NAME, TRAILING_STOP_CHECK_EVERY, every_tenant(self._tenants, self._follow_of)
        )
