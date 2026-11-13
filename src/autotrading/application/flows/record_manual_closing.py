import logging
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import ClosedPositionRepositoryPort, FlowOpeningsPort, FlowRepositoryPort
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class RecordManualClosingCommand:
    account_id: UUID
    asset: str
    fill: ClosingFill | None


class RecordManualClosingUseCase:
    """A position a user closed by hand enters the history of the flow that trades its asset (R1.7.2, ADR 0061).

    A closing the exchange did not confirm in time leaves the position as the exchange shows it: nothing to record.
    The asset conflict rule leaves at most one flow not archived on an asset of an account (R1.1.2): that flow takes
    the closing. A position no flow trades, or one the flow never opened, has no history to enter.
    """

    def __init__(
        self, flows: FlowRepositoryPort, openings: FlowOpeningsPort, closed_positions: ClosedPositionRepositoryPort
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._closed_positions = closed_positions

    def execute(self, command: RecordManualClosingCommand) -> None:
        if command.fill is None:
            return
        fill = command.fill
        owners = [
            flow
            for flow in self._flows.list()
            if flow.account_id == command.account_id
            and flow.status != FlowStatus.ARCHIVED
            and command.asset in flow.configuration.assets
        ]
        if not owners:
            return
        flow = owners[0]
        opening = self._openings.last_opening(flow.id, command.asset)
        if opening is None:
            operations.warning(
                "posizione chiusa a mano senza apertura del flusso",
                extra={"flow_id": str(flow.id.value), "asset": command.asset},
            )
            return
        self._closed_positions.add(opening.closed(flow, command.asset, fill, CloseReason.MANUAL))
