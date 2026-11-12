from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from autotrading.adapters.outbound.hyperliquid.user_state import UserPosition, UserState, decimal_of, user_state_of

SHORT_ETH = {
    "coin": "ETH",
    "szi": "-1.5",
    "leverage": {"type": "isolated", "value": 3},
    "entryPx": "3000.0",
    "unrealizedPnl": "-4.5",
    "marginUsed": "1500.0",
    "liquidationPx": "3900.0",
}
STATE = {
    "marginSummary": {"accountValue": "1012.5"},
    "withdrawable": "862.5",
    "assetPositions": [{"type": "oneWay", "position": SHORT_ETH}],
    "time": 1762941600000,
}


def test_the_state_is_read_once_with_every_field_the_adapters_need() -> None:
    assert user_state_of(STATE) == UserState(
        account_value=Decimal("1012.5"),
        withdrawable=Decimal("862.5"),
        positions=(
            UserPosition(
                coin="ETH",
                signed_size=Decimal("-1.5"),
                leverage=3,
                entry_price=Decimal(3000),
                unrealized_pnl=Decimal("-4.5"),
                margin=Decimal(1500),
                liquidation_price=Decimal(3900),
            ),
        ),
        read_at=datetime(2025, 11, 12, 10, 0, tzinfo=UTC),
    )


def test_a_position_without_a_liquidation_price_reads_none() -> None:
    state = STATE | {"assetPositions": [{"position": SHORT_ETH | {"liquidationPx": None}}]}

    (position,) = user_state_of(state).positions

    assert position.liquidation_price is None


@pytest.mark.parametrize("missing", ["szi", "leverage", "entryPx", "unrealizedPnl", "marginUsed", "coin"])
def test_a_position_missing_a_field_is_refused(missing: str) -> None:
    position = {key: value for key, value in SHORT_ETH.items() if key != missing}

    with pytest.raises(KeyError):
        user_state_of(STATE | {"assetPositions": [{"position": position}]})


def test_a_number_keeps_every_digit_the_exchange_sends() -> None:
    value: Any = 0.1

    assert decimal_of(value) == Decimal("0.1")
