from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
import requests
from eth_account import Account as EthereumAccount
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import INVALID_KEY_MESSAGE, TIMEOUT_SECONDS
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.application.orders.errors import (
    ExchangeRejectedOrderError,
    OrderExchangeUnavailableError,
    OrderNotAcknowledgedError,
)
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess

BASE_URL = "https://api.hyperliquid-testnet.xyz"
WALLET = EthereumAccount.create()
ADDRESS = "0xAbCdEf0000000000000000000000000000000001"
ACCESS = TradingAccess("Hyperliquid", ADDRESS, WALLET.key.hex())
OID = 77747314
META = {
    "universe": [
        {"name": "BTC", "szDecimals": 5, "maxLeverage": 40},
        {"name": "ETH", "szDecimals": 4, "maxLeverage": 25},
    ]
}
MIDS = {"BTC": "100000.0", "ETH": "4000.5"}
OK = {"status": "ok", "response": {"type": "default"}}
FILLED = {
    "status": "ok",
    "response": {
        "type": "order",
        "data": {"statuses": [{"filled": {"totalSz": "0.0003", "avgPx": "100010.0", "oid": OID}}]},
    },
}
FILLS = [
    {
        "coin": "BTC",
        "px": "100000.0",
        "sz": "0.0001",
        "oid": OID,
        "fee": "0.0045",
        "closedPnl": "0.0",
        "time": 1_794_307_200_000,
    },
    {
        "coin": "BTC",
        "px": "100015.0",
        "sz": "0.0002",
        "oid": OID,
        "fee": "0.009",
        "closedPnl": "0.25",
        "time": 1_794_307_200_400,
    },
    {"coin": "ETH", "px": "4000.0", "sz": "1.0", "oid": 1, "fee": "1.8", "closedPnl": "0.0", "time": 1_794_307_100_000},
]

STATE = {
    "assetPositions": [
        {"position": {"coin": "BTC", "szi": "-0.0003", "leverage": {"type": "cross", "value": 3}}},
        {"position": {"coin": "ETH", "szi": "1.25", "leverage": {"type": "cross", "value": 5}}},
        {"position": {"coin": "SOL", "szi": "0.0", "leverage": {"type": "cross", "value": 2}}},
    ]
}


def answer(statuses: list[Any]) -> Any:
    return {"status": "ok", "response": {"type": "order", "data": {"statuses": statuses}}}


@dataclass
class FakeSdk:
    """Stands in for the official SDK: it records the calls and answers what the test decides."""

    order_answer: Any = field(default_factory=lambda: FILLED)
    leverage_answer: Any = field(default_factory=lambda: OK)
    fills: Any = field(default_factory=lambda: FILLS)
    order_status: Any = field(
        default_factory=lambda: {"status": "order", "order": {"order": {"oid": OID}, "status": "filled"}}
    )
    meta_answer: Any = field(default_factory=lambda: META)
    state: Any = field(default_factory=lambda: STATE)
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        self.calls.append(("exchange", (wallet.address, base_url, account_address, timeout)))
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        return self

    def _answer(self, name: str, arguments: Any, value: Any) -> Any:
        self.calls.append((name, arguments))
        if self.failure is not None:
            raise self.failure
        return value

    def meta(self) -> Any:
        return self._answer("meta", (), self.meta_answer)

    def all_mids(self) -> Any:
        return self._answer("all_mids", (), MIDS)

    def update_leverage(self, leverage: int, coin: str, is_cross: bool) -> Any:
        return self._answer("update_leverage", (leverage, coin, is_cross), self.leverage_answer)

    def market_open(self, *arguments: Any) -> Any:
        *sent, cloid = arguments
        return self._answer("market_open", (*sent, str(cloid)), self.order_answer)

    def market_close(self, coin: str, size: float, px: None, slippage: float, cloid: object) -> Any:
        return self._answer("market_close", (coin, size, px, slippage, str(cloid)), self.order_answer)

    def user_fills(self, address: str) -> Any:
        self.calls.append(("user_fills", address))
        return self.fills

    def user_state(self, address: str) -> Any:
        return self._answer("user_state", address, self.state)

    def query_order_by_cloid(self, address: str, cloid: object) -> Any:
        return self._answer("query_order_by_cloid", (address, str(cloid)), self.order_status)


def an_order(*, reduce_only: bool = False) -> MarketOrder:
    return MarketOrder("BTC", Direction.SHORT, Decimal("0.0003"), Slippage.percent(Decimal(2)), reduce_only=reduce_only)


def adapter(sdk: FakeSdk) -> HyperliquidOrderExchangeAdapter:
    return HyperliquidOrderExchangeAdapter(BASE_URL, sdk)


def calls_named(sdk: FakeSdk, name: str) -> list[Any]:
    return [arguments for called, arguments in sdk.calls if called == name]


def test_the_market_carries_leverage_size_decimals_and_mid_price() -> None:
    assert adapter(FakeSdk()).market(ACCESS, "ETH") == Market("ETH", 25, 4, Decimal("4000.5"))


def test_an_asset_the_exchange_does_not_list_is_refused_as_unknown() -> None:
    with pytest.raises(ExchangeRejectedOrderError) as raised:
        adapter(FakeSdk()).market(ACCESS, "DOGE")

    assert raised.value.exchange_message == "Unknown asset DOGE"


def test_metadata_of_unexpected_shape_are_unavailable() -> None:
    sdk = FakeSdk(meta_answer={"universe": [{"name": "BTC", "szDecimals": "five", "maxLeverage": 40}]})

    with pytest.raises(OrderExchangeUnavailableError):
        adapter(sdk).market(ACCESS, "BTC")


def test_the_leverage_is_set_in_cross_with_the_wallet_of_the_access() -> None:
    sdk = FakeSdk()

    adapter(sdk).set_leverage(ACCESS, "BTC", 3)

    assert calls_named(sdk, "update_leverage") == [(3, "BTC", True)]
    assert calls_named(sdk, "exchange") == [(WALLET.address, BASE_URL, ADDRESS, TIMEOUT_SECONDS)]


def test_a_refused_leverage_keeps_the_message_of_the_exchange_without_the_address() -> None:
    sdk = FakeSdk(leverage_answer={"status": "err", "response": f"Invalid leverage for {ADDRESS.lower()}"})

    with pytest.raises(ExchangeRejectedOrderError) as raised:
        adapter(sdk).set_leverage(ACCESS, "BTC", 99)

    assert raised.value.exchange_message == "Invalid leverage for ***"


def test_an_opening_order_is_sent_at_market_with_its_cloid_and_slippage() -> None:
    sdk = FakeSdk()
    order = an_order()

    adapter(sdk).place_market_order(ACCESS, order)

    assert calls_named(sdk, "market_open") == [("BTC", False, 0.0003, None, 0.02, order.id.hex)]


def test_a_reduce_only_order_closes_the_position() -> None:
    sdk = FakeSdk()
    order = an_order(reduce_only=True)

    adapter(sdk).place_market_order(ACCESS, order)

    assert calls_named(sdk, "market_close") == [("BTC", 0.0003, None, 0.02, order.id.hex)]
    assert calls_named(sdk, "market_open") == []


def test_the_execution_is_read_from_the_fills_of_the_order() -> None:
    execution = adapter(FakeSdk()).place_market_order(ACCESS, an_order())

    assert execution == Execution(
        filled_size=Decimal("0.0003"),
        average_price=Decimal(100010),
        fee=Decimal("0.0135"),
        realized_pnl=Decimal("0.25"),
        executed_at=datetime.fromtimestamp(1_794_307_200.4, UTC),
    )


def test_a_filled_order_without_fills_yet_is_not_acknowledged() -> None:
    with pytest.raises(OrderNotAcknowledgedError):
        adapter(FakeSdk(fills=[])).place_market_order(ACCESS, an_order())


@pytest.mark.parametrize(
    "message",
    ["Order could not immediately match against any resting orders. asset=0", "Order must have minimum value of $10."],
)
def test_an_order_refused_by_the_exchange_keeps_its_message(message: str) -> None:
    with pytest.raises(ExchangeRejectedOrderError) as raised:
        adapter(FakeSdk(order_answer=answer([{"error": message}]))).place_market_order(ACCESS, an_order())

    assert raised.value.exchange_message == message


def test_a_refusal_of_the_whole_request_keeps_its_message() -> None:
    sdk = FakeSdk(order_answer={"status": "err", "response": "Insufficient margin to place order."})

    with pytest.raises(ExchangeRejectedOrderError) as raised:
        adapter(sdk).place_market_order(ACCESS, an_order())

    assert raised.value.exchange_message == "Insufficient margin to place order."


@pytest.mark.parametrize("statuses", [[{"resting": {"oid": OID}}], [], [{"filled": {"oid": "x"}}]])
def test_an_order_answer_of_unexpected_shape_is_unavailable(statuses: list[Any]) -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(order_answer=answer(statuses))).place_market_order(ACCESS, an_order())


def test_an_order_without_answer_in_time_is_not_acknowledged() -> None:
    with pytest.raises(OrderNotAcknowledgedError):
        adapter(FakeSdk(failure=requests.ReadTimeout())).place_market_order(ACCESS, an_order())


def test_a_timeout_outside_the_order_is_an_unavailable_exchange() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(failure=requests.ReadTimeout())).market(ACCESS, "BTC")


@pytest.mark.parametrize("failure", [ServerError(502, "bad gateway"), requests.ConnectionError()])
def test_a_fault_of_the_exchange_or_of_the_network_is_unavailable(failure: Exception) -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(failure=failure)).place_market_order(ACCESS, an_order())


def test_an_error_of_the_client_is_a_refusal_without_the_secret() -> None:
    failure = ClientError(422, None, f"bad signer {WALLET.key.hex()}", None)

    with pytest.raises(ExchangeRejectedOrderError) as raised:
        adapter(FakeSdk(failure=failure)).place_market_order(ACCESS, an_order())

    assert raised.value.exchange_message == "bad signer ***"


def test_an_invalid_key_is_refused_before_reaching_the_exchange() -> None:
    sdk = FakeSdk()

    with pytest.raises(ExchangeRejectedOrderError) as raised:
        adapter(sdk).place_market_order(TradingAccess("Hyperliquid", ADDRESS, "not-a-key"), an_order())

    assert raised.value.exchange_message == INVALID_KEY_MESSAGE
    assert calls_named(sdk, "market_open") == []


def test_an_order_is_looked_up_by_its_cloid_and_its_fills() -> None:
    sdk = FakeSdk()
    order = an_order()

    execution = adapter(sdk).find_order(ACCESS, order)

    assert calls_named(sdk, "query_order_by_cloid") == [(ADDRESS, order.id.hex)]
    assert execution is not None
    assert execution.filled_size == Decimal("0.0003")


def test_an_order_the_exchange_does_not_know_is_none() -> None:
    assert adapter(FakeSdk(order_status={"status": "unknownOid"})).find_order(ACCESS, an_order()) is None


def test_an_order_found_without_fills_is_none() -> None:
    sdk = FakeSdk(fills=[], order_status={"status": "order", "order": {"order": {"oid": OID}, "status": "canceled"}})

    assert adapter(sdk).find_order(ACCESS, an_order()) is None


def test_an_order_status_of_unexpected_shape_is_unavailable() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(order_status={"status": "order"})).find_order(ACCESS, an_order())


def test_fills_of_unexpected_shape_are_unavailable() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(fills=[{"oid": OID, "sz": "0.1"}])).place_market_order(ACCESS, an_order())


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_network_is_chosen_by_the_installation(testnet: bool, url: str) -> None:
    sdk = FakeSdk()

    HyperliquidOrderExchangeAdapter.for_network(testnet=testnet, sdk=sdk).market(ACCESS, "BTC")

    assert calls_named(sdk, "info") == [(url, TIMEOUT_SECONDS)]


@pytest.mark.parametrize(
    ("coin", "expected"),
    [
        ("BTC", HeldPosition("BTC", Direction.SHORT, Decimal("0.0003"), 3)),
        ("ETH", HeldPosition("ETH", Direction.LONG, Decimal("1.25"), 5)),
    ],
)
def test_the_position_is_read_from_the_state_of_the_account(coin: str, expected: HeldPosition) -> None:
    sdk = FakeSdk()

    assert adapter(sdk).position(ACCESS, coin) == expected
    assert calls_named(sdk, "user_state") == [ADDRESS]


@pytest.mark.parametrize("coin", ["SOL", "DOGE"])
def test_an_asset_without_size_or_not_held_has_no_position(coin: str) -> None:
    assert adapter(FakeSdk()).position(ACCESS, coin) is None


def test_a_state_of_unexpected_shape_is_unavailable() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(state={"assetPositions": [{"position": {"coin": "BTC"}}]})).position(ACCESS, "BTC")


def test_a_fault_reading_the_position_is_unavailable() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(failure=ServerError(500, "down"))).position(ACCESS, "BTC")
