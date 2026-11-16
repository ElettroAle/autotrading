from dataclasses import dataclass

from autotrading.domain.flows.closed_position import ClosedPosition

CLOSED_POSITIONS_PER_PAGE = 50


@dataclass(frozen=True, slots=True)
class ClosedPositionPage:
    """A page of the closed positions of a flow that match a filter, from the most recent close, and how many match
    in all (R1.7.2, R2.2.5, R6.4.4).
    """

    number: int
    positions: tuple[ClosedPosition, ...]
    has_next: bool
    total: int
