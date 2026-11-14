from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import EquitySnapshotRepositoryPort
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.equity_snapshot import EquitySnapshot


class RecordCycleEquityUseCase:
    """The equity of the flow at the cycle, from the state attributed to it the cycle read last (R2.2.3, ADR 0120)."""

    def __init__(self, equity: EquitySnapshotRepositoryPort) -> None:
        self._equity = equity

    def execute(
        self,
        flow_id: UUID,  # noqa: ARG002 - the signature of the port: the state names its flow
        planned_at: datetime,
        state: CycleFlow,
    ) -> None:
        self._equity.record(EquitySnapshot.of_state(planned_at, state.attributed))
