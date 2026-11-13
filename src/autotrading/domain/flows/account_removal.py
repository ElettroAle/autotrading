from collections.abc import Sequence

from autotrading.domain.flows.errors import (
    FlowPositionsLeftOpenError,
    OpenPositionsNeedConfirmationError,
    OperatingFlowsNeedConfirmationError,
)
from autotrading.domain.flows.stop_outcome import PositionLeftOpen


def require_confirmation_for_positions(assets: Sequence[str]) -> None:
    """An account with open positions is removed only with an explicit confirmation (R0.2.5)."""
    if assets:
        raise OpenPositionsNeedConfirmationError


def require_confirmation_for_flows(flows: Sequence[str]) -> None:
    """An account with flows still operating on it is removed only with an explicit confirmation (R1.1.8)."""
    if flows:
        raise OperatingFlowsNeedConfirmationError(tuple(flows))


def require_all_closed(left_open: Sequence[PositionLeftOpen]) -> None:
    """A position left open keeps the account: without it nobody could close the position from the platform."""
    if left_open:
        raise FlowPositionsLeftOpenError(tuple((position.asset, position.reason) for position in left_open))
