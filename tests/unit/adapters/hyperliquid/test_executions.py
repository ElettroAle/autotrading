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

from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidSdkAdapter
from autotrading.adapters.outbound.hyperliquid.executions import (
    FILLS_KEPT,
    FILLS_PAGE,
    FUNDING_PAGE,
    MOVEMENTS_PAGE,
    HyperliquidAccountExecutionsAdapter,
)
from autotrading.application.flows.errors import FlowCredentialsFieldMissingError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.ledger import BalanceMovement, Execution, FundingPayment

ADDRESS = "0x00000000000000000000000000000000000000Aa"
OTHER = "0x00000000000000000000000000000000000000bb"
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


def an_update(time: int, delta: dict[str, Any], hash_: str = "0xfeed") -> dict[str, Any]:
    return {"time": time, "hash": hash_, "delta": delta}


@dataclass
class FakeSdk(HyperliquidSdkAdapter):
    fill_pages: list[list[dict[str, Any]]] = field(default_factory=lambda: [[a_fill(7, 1762941500000)]])
    funding_pages: list[list[dict[str, Any]]] = field(default_factory=lambda: [[a_payment(1762941600000)]])
    ledger_pages: list[Any] = field(default_factory=lambda: [[]])
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

    def user_non_funding_ledger_updates(
        self,
        user: str,
        startTime: int,  # noqa: N803 - the SDK names it
        endTime: int | None = None,  # noqa: N803 - the SDK names it
    ) -> Any:
        self.calls.append(("user_non_funding_ledger_updates", (user, startTime, endTime)))
        return self.ledger_pages.pop(0)


def read(sdk: FakeSdk, since: datetime | None = SINCE) -> Any:
    return read_reference(sdk, AccountReference({"account_address": ADDRESS}), since)


def read_reference(sdk: FakeSdk, reference: AccountReference, since: datetime | None = SINCE) -> Any:
    return HyperliquidAccountExecutionsAdapter("https://exchange.invalid", sdk, 3.0).since(reference, since)


def test_the_executions_are_found_by_the_address_alone() -> None:
    adapter = HyperliquidAccountExecutionsAdapter("https://exchange.invalid", FakeSdk(), 3.0)

    assert adapter.reference_fields() == frozenset({"account_address"})


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
    assert ("user_non_funding_ledger_updates", (ADDRESS, SINCE_MS, None)) in sdk.calls
    assert all(call[0] != "exchange" for call in sdk.calls)


def test_without_a_moment_everything_the_exchange_keeps_is_asked() -> None:
    sdk = FakeSdk()

    window = read(sdk, None)

    assert ("user_fills_by_time", (ADDRESS, 0)) in sdk.calls
    assert ("user_non_funding_ledger_updates", (ADDRESS, 0, None)) in sdk.calls
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


def test_the_movements_are_read_page_after_page() -> None:
    deposit = {"type": "deposit", "usdc": "1"}
    deposits = [an_update(3000 + index, deposit, f"0x{index}") for index in range(MOVEMENTS_PAGE)]
    sdk = FakeSdk(ledger_pages=[deposits, [an_update(9000, {"type": "deposit", "usdc": "2"})]])

    window = read(sdk)

    assert len(window.movements) == MOVEMENTS_PAGE + 1
    pages = [call[1][1] for call in sdk.calls if call[0] == "user_non_funding_ledger_updates"]
    assert pages == [SINCE_MS, 3000 + MOVEMENTS_PAGE]


# ADR movimenti-del-conto-nel-registro-con-cursore: the movements of the balance travel with the executions.
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
    (movement,) = read(FakeSdk(ledger_pages=[[an_update(1762941000000, delta)]])).movements

    assert movement == BalanceMovement("0xfeed", amount, datetime(2025, 11, 12, 9, 50, tzinfo=UTC))


def test_a_ledger_update_that_moves_no_balance_is_not_a_movement() -> None:
    update = an_update(1, {"type": "liquidation", "accountValue": "3"})

    assert read(FakeSdk(ledger_pages=[[update]])).movements == ()


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
        FakeSdk(ledger_pages=[[{"time": 1, "delta": {"type": "deposit", "usdc": "1"}}]]),
        FakeSdk(ledger_pages=[None]),
    ],
    ids=["fill without fields", "cloid not hex", "payment without fields", "movement without hash", "no ledger"],
)
def test_an_answer_of_unexpected_shape_is_unavailable(sdk: FakeSdk) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        read(sdk)


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_executions_are_read_on_the_network_asked(*, testnet: bool, url: str) -> None:
    adapter = HyperliquidAccountExecutionsAdapter.for_network(testnet=testnet, sdk=FakeSdk())

    assert adapter.base_url == url


def test_a_reference_without_the_address_is_refused_before_reaching_the_exchange() -> None:
    sdk = FakeSdk()

    with pytest.raises(FlowCredentialsFieldMissingError):
        read_reference(sdk, AccountReference({"wallet": ADDRESS}))

    assert sdk.calls == []
