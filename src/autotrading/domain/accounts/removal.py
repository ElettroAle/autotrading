from collections.abc import Sequence
from dataclasses import dataclass

from autotrading.domain.accounts.errors import (
    FlowPositionsLeftOpenError,
    OpenPositionsNeedConfirmationError,
    OperatingFlowsNeedConfirmationError,
)
from autotrading.domain.accounts.position import Position


@dataclass(frozen=True, slots=True)
class FlowPositionLeftOpen:
    """A position of a flow of the account the exchange did not close, with the reason it gave (R1.1.8)."""

    asset: str
    reason: str


def require_confirmation_for(positions: Sequence[Position]) -> None:
    """An account with open positions is removed only with an explicit confirmation (R0.2.5)."""
    if positions:
        raise OpenPositionsNeedConfirmationError


def require_confirmation_for_flows(flows: Sequence[str]) -> None:
    """An account with flows still operating on it is removed only with an explicit confirmation (R1.1.8)."""
    if flows:
        raise OperatingFlowsNeedConfirmationError(tuple(flows))


def require_all_closed(left_open: Sequence[FlowPositionLeftOpen]) -> None:
    """A position left open keeps the account: without it nobody could close the position from the platform."""
    if left_open:
        raise FlowPositionsLeftOpenError(tuple((position.asset, position.reason) for position in left_open))
