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

from autotrading.adapters.outbound.hyperliquid.executions import (
    FILLS_KEPT,
    FILLS_PAGE,
    FUNDING_PAGE,
    HyperliquidAccountExecutionsAdapter,
)
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.ledger import Execution, FundingPayment

ADDRESS = "0x00000000000000000000000000000000000000Aa"
CLOID = "0x1234567890abcdef1234567890abcdef"
SINCE = datetime(2025, 11, 12, 9, 0, tzinfo=UTC)
SINCE_MS = 1762938000000


def a_fill(tid: int, time: int, **changes: Any) -> dict[str, Any]:
    fill = {
        "tid": tid,
        "oid": 900 + tid,
        "coin": "BTC",
        "side": "B",
        "sz": "0.001",
        "px": "100000",
        "fee": "0.04",
        "closedPnl": "2.5",
        "startPosition": "0.002",
        "time": time,
        "cloid": CLOID,
    }
    return {**fill, **changes}


def a_payment(time: int, coin: str = "BTC", usdc: str = "-0.3") -> dict[str, Any]:
    return {"time": time, "hash": "0x0", "delta": {"type": "funding", "coin": coin, "usdc": usdc, "szi": "0.002"}}


@dataclass
class FakeSdk:
    fill_pages: list[list[dict[str, Any]]] = field(default_factory=lambda: [[a_fill(7, 1762941500000)]])
    funding_pages: list[list[dict[str, Any]]] = field(default_factory=lambda: [[a_payment(1762941600000)]])
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        self.calls.append(("exchange", (wallet.address, base_url, account_address, timeout)))
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        return self

    def user_fills_by_time(self, address: str, start_time: int) -> Any:
        if self.failure is not None:
            raise self.failure
        self.calls.append(("user_fills_by_time", (address, start_time)))
        return self.fill_pages.pop(0)

    def user_funding_history(self, user: str, startTime: int) -> Any:  # noqa: N803 - the SDK names it
        self.calls.append(("user_funding_history", (user, startTime)))
        return self.funding_pages.pop(0)


def read(sdk: FakeSdk, since: datetime | None = SINCE) -> Any:
    return HyperliquidAccountExecutionsAdapter("https://exchange.invalid", sdk, 3.0).since(ADDRESS, since)


def test_an_execution_carries_what_the_ledger_needs() -> None:
    (execution,) = read(FakeSdk()).executions

    assert execution == Execution(
        fill_id="7",
        exchange_order_id="907",
        order_id=UUID("12345678-90ab-cdef-1234-567890abcdef"),
        asset="BTC",
        size=Decimal("0.001"),
        price=Decimal(100000),
        fee=Decimal("0.04"),
        realized_pnl=Decimal("2.5"),
        start_position=Decimal("0.002"),
        liquidation=False,
        executed_at=datetime(2025, 11, 12, 9, 58, 20, tzinfo=UTC),
    )


def test_a_sale_has_a_negative_size() -> None:
    (execution,) = read(FakeSdk(fill_pages=[[a_fill(1, 1000, side="A")]])).executions

    assert execution.size == Decimal("-0.001")


def test_an_execution_without_a_client_order_id_has_no_order() -> None:
    fill = a_fill(1, 1000)
    del fill["cloid"]

    (execution,) = read(FakeSdk(fill_pages=[[fill]])).executions

    assert execution.order_id is None


def test_a_liquidation_is_marked() -> None:
    liquidation = {"liquidatedUser": ADDRESS, "markPx": "90000", "method": "market"}

    (execution,) = read(FakeSdk(fill_pages=[[a_fill(1, 1000, liquidation=liquidation)]])).executions

    assert execution.liquidation


def test_a_funding_payment_carries_asset_amount_and_moment() -> None:
    (payment,) = read(FakeSdk()).funding

    assert payment == FundingPayment("BTC", Decimal("-0.3"), datetime(2025, 11, 12, 10, 0, tzinfo=UTC))


def test_only_what_is_newer_than_the_moment_is_asked() -> None:
    sdk = FakeSdk()

    read(sdk)

    assert ("user_fills_by_time", (ADDRESS, SINCE_MS)) in sdk.calls
    assert ("user_funding_history", (ADDRESS, SINCE_MS)) in sdk.calls
    assert all(call[0] != "exchange" for call in sdk.calls)


def test_without_a_moment_everything_the_exchange_keeps_is_asked() -> None:
    sdk = FakeSdk()

    window = read(sdk, None)

    assert ("user_fills_by_time", (ADDRESS, 0)) in sdk.calls
    assert window.complete


def test_the_executions_and_the_funding_are_read_page_after_page() -> None:
    fills = [a_fill(index, 1000 + index) for index in range(FILLS_PAGE)]
    payments = [a_payment(2000 + index) for index in range(FUNDING_PAGE)]
    sdk = FakeSdk(fill_pages=[fills, [a_fill(9999, 5000)]], funding_pages=[payments, []])

    window = read(sdk)

    assert (len(window.executions), len(window.funding)) == (FILLS_PAGE + 1, FUNDING_PAGE)
    fill_pages = [call[1][1] for call in sdk.calls if call[0] == "user_fills_by_time"]
    funding_pages = [call[1][1] for call in sdk.calls if call[0] == "user_funding_history"]
    assert fill_pages == [SINCE_MS, 1000 + FILLS_PAGE]
    assert funding_pages == [SINCE_MS, 2000 + FUNDING_PAGE]


def test_as_many_executions_as_the_exchange_keeps_since_the_moment_make_the_window_incomplete() -> None:
    pages = [
        [a_fill(page * FILLS_PAGE + index, page * FILLS_PAGE + index) for index in range(FILLS_PAGE)]
        for page in range(5)
    ]

    window = read(FakeSdk(fill_pages=[*pages, []]))

    assert len(window.executions) == FILLS_KEPT
    assert not window.complete


def test_fewer_executions_than_the_exchange_keeps_make_the_window_complete() -> None:
    assert read(FakeSdk()).complete


def test_from_the_start_a_full_history_is_the_starting_point() -> None:
    pages = [
        [a_fill(page * FILLS_PAGE + index, page * FILLS_PAGE + index) for index in range(FILLS_PAGE)]
        for page in range(5)
    ]

    assert read(FakeSdk(fill_pages=[*pages, []]), None).complete


@pytest.mark.parametrize(
    "failure",
    [ClientError(429, "429", "rate limited", None, None), ServerError(500, "boom"), requests.ConnectionError("down")],
)
def test_an_exchange_that_cannot_answer_is_unavailable(failure: Exception) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(FakeSdk(failure=failure))


@pytest.mark.parametrize(
    "sdk",
    [
        FakeSdk(fill_pages=[[{"tid": 1}]]),
        FakeSdk(fill_pages=[[a_fill(1, 1, cloid="0xnothex")]]),
        FakeSdk(funding_pages=[[{"time": 1, "delta": {"type": "funding"}}]]),
    ],
    ids=["fill without fields", "cloid not hex", "payment without fields"],
)
def test_an_answer_of_unexpected_shape_is_unavailable(sdk: FakeSdk) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(sdk)


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_executions_are_read_on_the_network_asked(*, testnet: bool, url: str) -> None:
    adapter = HyperliquidAccountExecutionsAdapter.for_network(testnet=testnet, sdk=FakeSdk())

    assert adapter.base_url == url
