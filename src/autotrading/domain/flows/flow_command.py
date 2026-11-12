from enum import StrEnum

from autotrading.domain.flows.flow_status import FlowStatus


class FlowCommand(StrEnum):
    """What the user asks of a flow, with the one status each command starts from (R1.1.4)."""

    START = "avvia"
    PAUSE = "pausa"
    RESUME = "riprendi"

    @property
    def starts_from(self) -> FlowStatus:
        return _STARTS_FROM[self]

    @property
    def leads_to(self) -> FlowStatus:
        return _LEADS_TO[self]


_STARTS_FROM = {
    FlowCommand.START: FlowStatus.STOPPED,
    FlowCommand.PAUSE: FlowStatus.ACTIVE,
    FlowCommand.RESUME: FlowStatus.PAUSED,
}
_LEADS_TO = {
    FlowCommand.START: FlowStatus.ACTIVE,
    FlowCommand.PAUSE: FlowStatus.PAUSED,
    FlowCommand.RESUME: FlowStatus.ACTIVE,
}
