from enum import StrEnum

from autotrading.domain.flows.flow_status import FlowStatus


class FlowCommand(StrEnum):
    """What the user asks of a flow, with the statuses each command starts from (R1.1.4, R1.1.5)."""

    START = "avvia"
    PAUSE = "pausa"
    RESUME = "riprendi"
    STOP = "ferma"

    @property
    def starts_from(self) -> frozenset[FlowStatus]:
        return _STARTS_FROM[self]

    @property
    def leads_to(self) -> FlowStatus:
        return _LEADS_TO[self]


_STARTS_FROM = {
    FlowCommand.START: frozenset({FlowStatus.STOPPED}),
    FlowCommand.PAUSE: frozenset({FlowStatus.ACTIVE}),
    FlowCommand.RESUME: frozenset({FlowStatus.PAUSED}),
    # A paused flow still holds its positions: stopping it closes them like for an active one (R1.1.5).
    FlowCommand.STOP: frozenset({FlowStatus.ACTIVE, FlowStatus.PAUSED}),
}
_LEADS_TO = {
    FlowCommand.START: FlowStatus.ACTIVE,
    FlowCommand.PAUSE: FlowStatus.PAUSED,
    FlowCommand.RESUME: FlowStatus.ACTIVE,
    FlowCommand.STOP: FlowStatus.STOPPED,
}
