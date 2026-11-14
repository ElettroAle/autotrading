from enum import StrEnum

from autotrading.domain.flows.flow_status import FlowStatus


class FlowAction(StrEnum):
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
    # A draft starts once account, capital and assets are assigned: the flow refuses it otherwise (ADR 0124).
    FlowAction.START: frozenset({FlowStatus.STOPPED, FlowStatus.DRAFT}),
    FlowAction.PAUSE: frozenset({FlowStatus.ACTIVE}),
    FlowAction.RESUME: frozenset({FlowStatus.PAUSED}),
    # A paused flow still holds its positions: stopping it closes them like for an active one (R1.1.5).
    FlowAction.STOP: frozenset({FlowStatus.ACTIVE, FlowStatus.PAUSED}),
}
_LEADS_TO = {
    FlowAction.START: FlowStatus.ACTIVE,
    FlowAction.PAUSE: FlowStatus.PAUSED,
    FlowAction.RESUME: FlowStatus.ACTIVE,
    FlowAction.STOP: FlowStatus.STOPPED,
}
