from collections.abc import Callable
from datetime import timedelta

from autotrading.application.flows.every_tenant import every_tenant
from autotrading.application.flows.ports import FlowTenantsPort, PeriodicCheckSchedulerPort
from autotrading.domain.tenancy.tenant_id import TenantId

OPEN_ACCOUNT_RECONCILIATION_NAME = "riconciliazione-dei-conti-con-posizioni-aperte"
# The interval of each account decides whether to read it: the check looks every minute, so a closing enters the
# history within the interval of its account plus at most a minute.
OPEN_ACCOUNT_RECONCILIATION_EVERY = timedelta(minutes=1)


class ScheduleOpenAccountReconciliationsUseCase:
    """Reconciles the accounts with open positions of every tenant when the worker starts, then every minute (Bug 778,
    ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte): the check of one tenant runs on the ports bound to
    it.
    """

    def __init__(
        self,
        scheduler: PeriodicCheckSchedulerPort,
        tenants: FlowTenantsPort,
        reconcile_of: Callable[[TenantId], None],
    ) -> None:
        self._scheduler = scheduler
        self._tenants = tenants
        self._reconcile_of = reconcile_of

    def execute(self) -> None:
        self._scheduler.keep_every(
            OPEN_ACCOUNT_RECONCILIATION_NAME,
            OPEN_ACCOUNT_RECONCILIATION_EVERY,
            every_tenant(self._tenants, self._reconcile_of),
        )
