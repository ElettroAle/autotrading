import logging

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    ExitPlanRepositoryPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    PositionClosedNoticePort,
    ProtectedPosition,
    ProtectionCancellationPort,
)
from autotrading.domain.flows.account_reconciliation import ProtectionClosing
from autotrading.domain.flows.errors import InvalidClosedPositionError
from autotrading.domain.flows.flow import Flow

operations = logging.getLogger("autotrading.flows")


class RecordProtectionClosingUseCase:
    """A position its stop loss or take profit closed on the exchange belongs to its flow: it ends its exit plan,
    enters the history with the reason of the protection and the outcome read from the exchange, is told, and the
    protection left on the exchange is cancelled (R3.1.2, ADR chiusure-per-protezione-nello-storico).

    The opening is the last order of the flow on the asset, as for a closing outside the platform (ADR 0056).
    """

    def __init__(  # noqa: PLR0913, PLR0917 - the history of the flow, its notice and the protections left
        self,
        flows: FlowRepositoryPort,
        openings: FlowOpeningsPort,
        closed_positions: ClosedPositionRepositoryPort,
        notice: PositionClosedNoticePort,
        exit_plans: ExitPlanRepositoryPort,
        protections: ProtectionCancellationPort,
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._closed_positions = closed_positions
        self._notice = notice
        self._exit_plans = exit_plans
        self._protections = protections

    def execute(self, closing: ProtectionClosing) -> None:
        flow = self._flows.get(closing.flow_id)
        self._exit_plans.remove(flow.id, closing.asset)
        self._record(flow, closing)
        self._protections.execute(ProtectedPosition(flow.assigned_account_id, closing.asset))

    def _record(self, flow: Flow, closing: ProtectionClosing) -> None:
        opening = self._openings.last_opening(flow.id, closing.asset)
        if opening is None:
            self._tell_without_history(flow, closing, "posizione chiusa da una protezione senza apertura del flusso")
            return
        try:
            closed = opening.closed_by_protection(flow, closing)
        except InvalidClosedPositionError:
            # A loss beyond the value the position held implies no price.
            self._tell_without_history(flow, closing, "esito della chiusura per protezione non rappresentabile")
            return
        self._closed_positions.add(closed)
        self._notice.execute(
            flow.id.value, flow.name.value, closed.asset, closed.pnl, closed.reason.value, closed.closing.at
        )

    def _tell_without_history(self, flow: Flow, closing: ProtectionClosing, reason: str) -> None:
        operations.warning(reason, extra={"flow_id": str(flow.id.value), "asset": closing.asset})
        self._notice.execute(
            flow.id.value,
            flow.name.value,
            closing.asset,
            closing.realized_pnl,
            closing.reason.value,
            closing.closed_at,
        )
