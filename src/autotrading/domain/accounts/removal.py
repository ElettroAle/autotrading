from collections.abc import Sequence

from autotrading.domain.accounts.errors import OpenPositionsNeedConfirmationError
from autotrading.domain.accounts.position import Position


def require_confirmation_for(positions: Sequence[Position]) -> None:
    """An account with open positions is removed only with an explicit confirmation (R0.2.5)."""
    if positions:
        raise OpenPositionsNeedConfirmationError
