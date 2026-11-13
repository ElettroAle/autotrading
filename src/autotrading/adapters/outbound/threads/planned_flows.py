import threading
from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from autotrading.application.cycles.errors import FlowOfCycleNotFoundError
from autotrading.application.cycles.ports import TenantScheduledFlow
from autotrading.domain.tenancy.tenant_id import TenantId


class ThreadsPlannedFlowsAdapter:
    """The tenant and the anchor of every flow the worker planned, shared by the threads of the cycles (ADR 0042).

    An entry is never forgotten, so a cycle still running finds its flow after the flow is paused.
    """

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._entries: dict[UUID, TenantScheduledFlow] = {}

    def remember(self, entries: Iterable[TenantScheduledFlow]) -> None:
        with self._guard:
            self._entries.update({entry.flow.flow_id: entry for entry in entries})

    def tenant_of(self, flow_id: UUID) -> TenantId:
        return self._entry(flow_id).tenant_id

    def anchor_of(self, flow_id: UUID) -> datetime:
        return self._entry(flow_id).flow.schedule.anchor

    def tenants(self) -> set[TenantId]:
        with self._guard:
            return {entry.tenant_id for entry in self._entries.values()}

    def _entry(self, flow_id: UUID) -> TenantScheduledFlow:
        with self._guard:
            entry = self._entries.get(flow_id)
        if entry is None:
            raise FlowOfCycleNotFoundError
        return entry
