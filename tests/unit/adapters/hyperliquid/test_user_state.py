from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from autotrading.adapters.outbound.hyperliquid.user_state import (
    _UserPosition,
    _UserState,
    decimal_of,
    in_account_mode,
    user_state_of,
)

SHORT_ETH = {
    "coin": "ETH",
    "szi": "-1.5",
    "leverage": {"type": "isolated", "value": 3},
    "entryPx": "3000.0",
    "positionValue": "4503.0",
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
    assert user_state_of(STATE) == _UserState(
        account_value=Decimal("1012.5"),
        withdrawable=Decimal("862.5"),
        positions=(
            _UserPosition(
                coin="ETH",
                signed_size=Decimal("-1.5"),
                leverage=3,
                entry_price=Decimal(3000),
                mark_price=Decimal(3002),
                unrealized_pnl=Decimal("-4.5"),
                margin=Decimal(1500),
                liquidation_price=Decimal(3900),
                isolated=True,
            ),
        ),
        read_at=datetime(2025, 11, 12, 10, 0, tzinfo=UTC),
    )


def test_the_mark_price_is_the_value_of_the_position_on_its_size() -> None:
    (position,) = user_state_of(STATE).positions

    assert position.mark_price == Decimal(3002)


def test_a_position_of_size_zero_is_an_answer_of_unexpected_shape() -> None:
    state = STATE | {"assetPositions": [{"position": SHORT_ETH | {"szi": "0.0"}}]}

    with pytest.raises(ArithmeticError):
        user_state_of(state)


def test_a_position_without_a_liquidation_price_reads_none() -> None:
    state = STATE | {"assetPositions": [{"position": SHORT_ETH | {"liquidationPx": None}}]}

    (position,) = user_state_of(state).positions

    assert position.liquidation_price is None


@pytest.mark.parametrize(
    "missing", ["szi", "leverage", "entryPx", "positionValue", "unrealizedPnl", "marginUsed", "coin"]
)
def test_a_position_missing_a_field_is_refused(missing: str) -> None:
    position = {key: value for key, value in SHORT_ETH.items() if key != missing}

    with pytest.raises(KeyError):
        user_state_of(STATE | {"assetPositions": [{"position": position}]})


def test_a_number_keeps_every_digit_the_exchange_sends() -> None:
    value: Any = 0.1

    assert decimal_of(value) == Decimal("0.1")


CROSS_BTC = {
    "coin": "BTC",
    "szi": "0.01",
    "leverage": {"type": "cross", "value": 5},
    "entryPx": "60000.0",
    "positionValue": "607.5",
    "unrealizedPnl": "7.5",
    "marginUsed": "120.0",
}
UNIFIED_PERPS = {
    "marginSummary": {"accountValue": "0.0"},
    "withdrawable": "0.0",
    "assetPositions": [{"type": "oneWay", "position": SHORT_ETH}, {"type": "oneWay", "position": CROSS_BTC}],
    "time": 1762941600000,
}
SPOT = {
    "balances": [
        {"coin": "PURR", "token": 1, "total": "2000.0", "hold": "0.0", "entryNtl": "0.0"},
        {"coin": "USDC", "token": 0, "total": "2999.0", "hold": "100.0", "entryNtl": "0.0"},
    ]
}


@pytest.mark.parametrize("mode", ["default", "disabled", "dexAbstraction", None])
def test_an_account_whose_perps_hold_their_own_balance_reads_it_from_the_perps_state(mode: object) -> None:
    perps = user_state_of(STATE)

    assert in_account_mode(perps, mode, SPOT) == perps


@pytest.mark.parametrize("mode", ["unifiedAccount", "portfolioMargin"])
def test_a_unified_account_reads_its_balance_from_the_usdc_it_holds(mode: str) -> None:
    perps = user_state_of(UNIFIED_PERPS)

    state = in_account_mode(perps, mode, SPOT)

    # 2999 USDC, which already holds the open result; available: 2999 - 100 on hold - 1500 of isolated margin.
    assert (state.account_value, state.withdrawable) == (Decimal("2999.0"), Decimal("1399.0"))
    assert (state.positions, state.read_at) == (perps.positions, perps.read_at)


def test_a_unified_account_without_usdc_has_no_balance() -> None:
    perps = user_state_of(UNIFIED_PERPS)

    state = in_account_mode(perps, "unifiedAccount", {"balances": []})

    assert (state.account_value, state.withdrawable) == (Decimal(0), Decimal(0))


# ADR-saldo-unified-comprensivo-del-risultato-aperto (Bug 597): the USDC total of the spot state already holds the
# open result, so the balance is that total and the open result is never added a second time. A reading of the testnet
# account of 20 November 2026, whose positions had an open result of -1.9346 USDC.
TESTNET_UNIFIED_PERPS = {
    "marginSummary": {"accountValue": "152.269011"},
    "withdrawable": "0.0",
    "assetPositions": [
        {"type": "oneWay", "position": {**CROSS_BTC, "unrealizedPnl": "-2.0", "marginUsed": "100.0"}},
        {"type": "oneWay", "position": {**CROSS_BTC, "coin": "ETH", "unrealizedPnl": "0.0654", "marginUsed": "52.0"}},
    ],
    "time": 1762941600000,
}
TESTNET_UNIFIED_SPOT = {"balances": [{"coin": "USDC", "token": 0, "total": "1007.303741", "hold": "152.269011"}]}


@pytest.mark.parametrize("mode", ["unifiedAccount", "portfolioMargin"])
def test_adr_saldo_unified_the_balance_is_the_usdc_total_without_adding_the_open_result_again(mode: str) -> None:
    state = in_account_mode(user_state_of(TESTNET_UNIFIED_PERPS), mode, TESTNET_UNIFIED_SPOT)

    assert state.account_value == Decimal("1007.303741")
    assert state.withdrawable == Decimal("855.034730")


@pytest.mark.parametrize(
    "spot", [{}, {"balances": [{"coin": "USDC"}]}, {"balances": [{"coin": "USDC", "total": "x", "hold": "0"}]}]
)
def test_a_spot_state_of_unexpected_shape_is_refused(spot: Any) -> None:
    with pytest.raises((KeyError, TypeError, ValueError, ArithmeticError)):
        in_account_mode(user_state_of(UNIFIED_PERPS), "unifiedAccount", spot)
