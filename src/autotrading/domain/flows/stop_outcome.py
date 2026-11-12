from dataclasses import dataclass

from autotrading.domain.flows.flow import Flow


@dataclass(frozen=True, slots=True)
class PositionLeftOpen:
    """A position of the flow the exchange did not close, with the reason it gave (R1.1.5)."""

    asset: str
    reason: str


@dataclass(frozen=True, slots=True)
class StopOutcome:
    """The flow stopped, whatever happened to its positions, and those still open on the exchange (R1.1.5)."""

    flow: Flow
    left_open: tuple[PositionLeftOpen, ...]
