from decimal import Decimal

import pytest

from autotrading.domain.accounts.errors import OpenPositionsNeedConfirmationError
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.accounts.removal import require_confirmation_for

SHORT_ETH = Position("ETH", PositionSide.SHORT, Decimal("1.5"), 3, Decimal(3000), Decimal("-4.2"), None)


def test_an_account_without_positions_needs_no_confirmation() -> None:
    require_confirmation_for(())


def test_an_account_with_any_open_position_needs_confirmation() -> None:
    with pytest.raises(OpenPositionsNeedConfirmationError):
        require_confirmation_for((SHORT_ETH,))
