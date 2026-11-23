from autotrading.application.notifications.errors import FlowStatusUnavailableError
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.notifications.flow_status import FlowStatusFigures, NotifiedFlowStatus, RecordedEquity
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.equity_snapshots import EquitySnapshotStore
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore


class FakeFlowStatusAdapter:
    """The state of the flows as their last cycles recorded it, by name; or a store that cannot be read."""

    def __init__(self) -> None:
        self.readable = True
        self.figures: dict[str, FlowStatusFigures] = {}
        self.asked: list[str] = []

    def status_of(self, flow_name: str) -> FlowStatusFigures | None:
        self.asked.append(flow_name)
        if not self.readable:
            raise FlowStatusUnavailableError
        return self.figures.get(flow_name)


class InMemoryFlowStatusAdapter:
    """The state of the flows of one tenant read from the stores the cycles write, as the SQL adapter reads its tables:
    the flow not archived with the name, the last equity recorded and the positions the ledger expects (ADR
    stato-del-flusso-in-ogni-notifica).
    """

    def __init__(
        self,
        flows: FlowStore,
        equity: EquitySnapshotStore,
        ledger: InMemoryFlowLedgerAdapter,
        tenant_id: TenantId,
        currency: str,
    ) -> None:
        self._flows = flows
        self._equity = equity
        self._ledger = ledger
        self._tenant_id = tenant_id
        self._currency = currency

    def status_of(self, flow_name: str) -> FlowStatusFigures | None:
        flow = self._flow_named(flow_name)
        if flow is None:
            return None
        last = self._last_equity(flow)
        recorded = None if last is None else RecordedEquity(last.equity, last.allocated_capital, last.cashed_profit)
        status = NotifiedFlowStatus[flow.status.name]
        return FlowStatusFigures(status, self._open_positions(flow), self._currency, recorded)

    def _flow_named(self, flow_name: str) -> Flow | None:
        return next(
            (
                flow
                for flow in self._flows.flows
                if flow.tenant_id == self._tenant_id
                and flow.name.value == flow_name
                and flow.status is not FlowStatus.ARCHIVED
            ),
            None,
        )

    def _last_equity(self, flow: Flow) -> EquitySnapshot | None:
        recorded = [
            snapshot
            for (tenant_id, owner, _), snapshot in self._equity.snapshots.items()
            if tenant_id == self._tenant_id and owner == flow.id.value
        ]
        return max(recorded, key=lambda snapshot: snapshot.planned_at, default=None)

    def _open_positions(self, flow: Flow) -> int:
        totals = self._ledger.totals_of([flow.id]).get(flow.id)
        return 0 if totals is None else sum(1 for size in totals.positions.values() if size != 0)
