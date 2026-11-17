import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.close_flow_positions import CloseFlowPositionsCommand, CloseFlowPositionsUseCase
from autotrading.application.flows.list_emergency_flows import ListEmergencyFlowsCommand, ListEmergencyFlowsUseCase
from autotrading.application.flows.ports import (
    AutomaticPausePort,
    EmergencyClosingLogPort,
    EmergencyClosingNoticePort,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.emergency_closing import (
    EMERGENCY_PAUSE_REASON,
    EmergencyClosing,
    EmergencyScope,
    FlowEmergencyOutcome,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class CloseInEmergencyCommand:
    scope: EmergencyScope
    # Who closes the positions: each closing order is recorded as theirs (R0.3.2).
    user_id: UserId


@dataclass(frozen=True, slots=True)
class EmergencyClosingPorts:
    flows: ListEmergencyFlowsUseCase
    pause: AutomaticPausePort
    closings: CloseFlowPositionsUseCase
    log: EmergencyClosingLogPort
    clock: Callable[[], datetime]
    notice: EmergencyClosingNoticePort


class CloseInEmergencyUseCase:
    """Closes every position of the flows of a scope and leaves them paused (R3.2.3, ADR chiusura-di-emergenza-per-
    ambito).

    The active flows pause first, with the reason of the emergency, so no cycle opens again; a paused flow keeps its
    pause and its reason. Then the positions of each flow close the way the stop and the cash-out close them: a
    closing that fails is reported with its flow and does not stop the others. The closing is recorded with its
    instant, its scope and its outcome, then told once: its positions are not told one by one (R3.5.1).
    """

    def __init__(self, tenant_id: TenantId, ports: EmergencyClosingPorts) -> None:
        self._tenant_id = tenant_id
        self._ports = ports

    def execute(self, command: CloseInEmergencyCommand) -> EmergencyClosing:
        flows = self._ports.flows.execute(ListEmergencyFlowsCommand(command.scope))
        self._ports.pause.pause([flow.id for flow in flows], EMERGENCY_PAUSE_REASON)
        outcomes = tuple(self._close(flow, command.user_id) for flow in flows)
        closing = EmergencyClosing(self._tenant_id, command.scope, self._ports.clock(), outcomes)
        self._ports.log.record(closing)
        self._ports.notice.execute(closing.positions_closed, closing.paused_flows)
        operations.warning(
            "chiusura di emergenza",
            extra={"scope": command.scope.kind.value, "flows": [str(flow.id.value) for flow in flows]},
        )
        return closing

    def _close(self, flow: Flow, user_id: UserId) -> FlowEmergencyOutcome:
        command = CloseFlowPositionsCommand(flow, user_id, CloseReason.EMERGENCY)
        try:
            closings = self._ports.closings.execute(command)
        except AutotradingError as error:
            # One flow that cannot be closed must not keep the others in the market (R3.2.3).
            return FlowEmergencyOutcome(flow.id, flow.name.value, failure=str(error))
        return FlowEmergencyOutcome(flow.id, flow.name.value, closings.closed, closings.left_open)
