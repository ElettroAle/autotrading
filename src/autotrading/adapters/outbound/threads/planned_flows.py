import threading
from collections.abc import Iterable

from autotrading.application.flows.ports import TenantScheduledFlow
from autotrading.domain.tenancy.tenant_id import TenantId


class ThreadsPlannedFlowsAdapter:
    """The tenants of every flow the worker planned, shared by the rounds of the worker (ADR 0042).

    A tenant is never forgotten, so the forecasts of a flow paused meanwhile still get their actual price.
    """

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._tenants: set[TenantId] = set()

    def remember(self, entries: Iterable[TenantScheduledFlow]) -> None:
        with self._guard:
            self._tenants.update(entry.tenant_id for entry in entries)

    def tenants(self) -> set[TenantId]:
        with self._guard:
            return set(self._tenants)
