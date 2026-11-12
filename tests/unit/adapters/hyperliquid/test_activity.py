from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
import requests
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.activity import FILLS_PAGE, HyperliquidAccountActivityAdapter
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountFill, AccountPosition, BalanceMovement
from autotrading.domain.flows.trade_intent import TradeSide

ADDRESS = "0x00000000000000000000000000000000000000Aa"
OTHER = "0x00000000000000000000000000000000000000bb"
CLOID = "0x1234567890abcdef1234567890abcdef"
STATE = {
    "marginSummary": {"accountValue": "1012.5"},
    "withdrawable": "862.5",
    "assetPositions": [
        {"position": {"coin": "BTC", "szi": "0.002", "marginUsed": "100.0", "unrealizedPnl": "12.5"}},
        {"position": {"coin": "ETH", "szi": "-0.5", "marginUsed": "50", "unrealizedPnl": "-3"}},
    ],
    "time": 1762941600000,
}


def a_fill(tid: int, time: int, cloid: str | None = CLOID) -> dict[str, Any]:
    fill = {"tid": tid, "coin": "BTC", "sz": "0.001", "px": "100000", "fee": "0.04", "closedPnl": "2.5", "time": time}
    return fill if cloid is None else {**fill, "cloid": cloid}


@dataclass
class FakeSdk:
    """Stands in for the official SDK: it answers what the test decides, or fails as the test decides."""

    state: Any = field(default_factory=lambda: STATE)
    fill_pages: list[list[dict[str, Any]]] = field(default_factory=lambda: [[a_fill(7, 1762941500000)]])
    ledger: Any = field(default_factory=list)
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        self.calls.append(("exchange", (wallet.address, base_url, account_address, timeout)))
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        return self

    def user_state(self, address: str) -> Any:
        if self.failure is not None:
            raise self.failure
        self.calls.append(("user_state", address))
        return self.state

    def user_fills_by_time(self, address: str, start_time: int) -> Any:
        self.calls.append(("user_fills_by_time", (address, start_time)))
        return self.fill_pages.pop(0)

    def user_non_funding_ledger_updates(self, user: str, startTime: int) -> Any:  # noqa: N803 - the SDK names it
        self.calls.append(("user_non_funding_ledger_updates", (user, startTime)))
        return self.ledger


def read(sdk: FakeSdk) -> Any:
    return HyperliquidAccountActivityAdapter("https://exchange.invalid", sdk, 3.0).activity(ADDRESS)


def test_the_totals_and_the_positions_are_those_of_the_exchange() -> None:
    activity = read(FakeSdk())

    assert (activity.currency, activity.balance, activity.available_margin) == (
        "USDC",
        Decimal("1012.5"),
        Decimal("862.5"),
    )
    assert activity.read_at == datetime(2025, 11, 12, 10, 0, tzinfo=UTC)
    assert activity.positions == (
        AccountPosition("BTC", TradeSide.LONG, Decimal("0.002"), Decimal("100.0"), Decimal("12.5")),
        AccountPosition("ETH", TradeSide.SHORT, Decimal("0.5"), Decimal(50), Decimal(-3)),
    )


def test_a_fill_carries_the_client_order_id_of_the_platform() -> None:
    (fill,) = read(FakeSdk()).fills

    assert fill == AccountFill(
        "7",
        UUID("12345678-90ab-cdef-1234-567890abcdef"),
        "BTC",
        Decimal("0.001"),
        Decimal(100000),
        Decimal("0.04"),
        Decimal("2.5"),
        datetime(2025, 11, 12, 9, 58, 20, tzinfo=UTC),
    )


def test_a_fill_without_a_client_order_id_has_no_order() -> None:
    (fill,) = read(FakeSdk(fill_pages=[[a_fill(1, 1000, cloid=None)]])).fills

    assert fill.order_id is None


def test_the_fills_are_read_page_after_page_from_the_start() -> None:
    first = [a_fill(index, 1000 + index) for index in range(FILLS_PAGE)]
    sdk = FakeSdk(fill_pages=[first, [a_fill(9999, 5000)]])

    fills = read(sdk).fills

    assert len(fills) == FILLS_PAGE + 1
    pages = [call[1] for call in sdk.calls if call[0] == "user_fills_by_time"]
    assert pages == [(ADDRESS, 0), (ADDRESS, 1000 + FILLS_PAGE)]


def test_the_activity_is_read_on_the_address_without_signing() -> None:
    sdk = FakeSdk()

    read(sdk)

    assert ("info", ("https://exchange.invalid", 3.0)) in sdk.calls
    assert ("user_state", ADDRESS) in sdk.calls
    assert ("user_non_funding_ledger_updates", (ADDRESS, 0)) in sdk.calls
    assert all(call[0] != "exchange" for call in sdk.calls)


@pytest.mark.parametrize(
    ("delta", "amount"),
    [
        ({"type": "deposit", "usdc": "200.0"}, Decimal(200)),
        ({"type": "withdraw", "usdc": "50", "fee": "1"}, Decimal(-50)),
        ({"type": "internalTransfer", "usdc": "10", "destination": ADDRESS.lower()}, Decimal(10)),
        ({"type": "internalTransfer", "usdc": "10", "destination": OTHER}, Decimal(-10)),
        ({"type": "subAccountTransfer", "usdc": "4", "destination": ADDRESS.upper()[2:].join(["0x", ""])}, Decimal(4)),
        ({"type": "subAccountTransfer", "usdc": "4", "destination": OTHER}, Decimal(-4)),
        ({"type": "accountClassTransfer", "usdc": "3", "toPerp": True}, Decimal(3)),
        ({"type": "accountClassTransfer", "usdc": "3", "toPerp": False}, Decimal(-3)),
    ],
)
def test_the_movements_of_the_balance_carry_their_sign(delta: dict[str, Any], amount: Decimal) -> None:
    ledger = [{"time": 1762941000000, "hash": "0xfeed", "delta": delta}]

    (movement,) = read(FakeSdk(ledger=ledger)).movements

    assert movement == BalanceMovement("0xfeed", amount, datetime(2025, 11, 12, 9, 50, tzinfo=UTC))


def test_a_ledger_update_that_moves_no_balance_is_not_a_movement() -> None:
    ledger = [{"time": 1, "hash": "0x1", "delta": {"type": "liquidation", "accountValue": "3"}}]

    assert read(FakeSdk(ledger=ledger)).movements == ()


@pytest.mark.parametrize(
    "failure",
    [
        ClientError(429, "429", "rate limited", None, None),
        ServerError(500, "boom"),
        requests.ConnectionError("down"),
        requests.Timeout("slow"),
    ],
)
def test_an_exchange_that_cannot_answer_is_unavailable(failure: Exception) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(FakeSdk(failure=failure))


@pytest.mark.parametrize(
    "sdk",
    [
        FakeSdk(state={"withdrawable": "1"}),
        FakeSdk(state={**STATE, "withdrawable": "many"}),
        FakeSdk(fill_pages=[[{"tid": 1}]]),
        FakeSdk(fill_pages=[[a_fill(1, 1, cloid="0xnothex")]]),
        FakeSdk(ledger=[{"time": 1, "delta": {"type": "deposit", "usdc": "1"}}]),
        FakeSdk(ledger=None),
    ],
    ids=["no summary", "not a number", "fill without fields", "cloid not hex", "movement without hash", "no ledger"],
)
def test_an_answer_of_unexpected_shape_is_unavailable(sdk: FakeSdk) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(sdk)


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_activity_is_read_on_the_network_asked(*, testnet: bool, url: str) -> None:
    assert HyperliquidAccountActivityAdapter.for_network(testnet=testnet, sdk=FakeSdk()).base_url == url
