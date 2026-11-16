from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest
import requests
from eth_account import Account as EthereumAccount
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError

from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS, HyperliquidSdkAdapter
from autotrading.adapters.outbound.hyperliquid.protections import HyperliquidProtectionExchangeAdapter
from autotrading.application.orders.errors import ExchangeRejectedOrderError, OrderExchangeUnavailableError
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.trading_access import TradingAccess

BASE_URL = "https://api.hyperliquid-testnet.xyz"
WALLET = EthereumAccount.create()
ADDRESS = "0xAbCdEf0000000000000000000000000000000001"
ACCESS = TradingAccess("Hyperliquid", {"account_address": ADDRESS, "secret_key": WALLET.key.hex()})
META = {"universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 40}]}
MIDS = {"BTC": "60000.0"}
STATE = {
    "assetPositions": [
        {"position": {"coin": "BTC", "szi": "0.0003", "entryPx": "60000", "leverage": {"type": "isolated", "value": 2}}}
    ]
}
STOP = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(57000))
OPEN_ORDERS = [
    {
        "coin": "BTC",
        "oid": 11,
        "orderType": "Stop Market",
        "isTrigger": True,
        "reduceOnly": True,
        "triggerPx": "57000.0",
    },
    {
        "coin": "BTC",
        "oid": 12,
        "orderType": "Take Profit Market",
        "isTrigger": True,
        "reduceOnly": True,
        "triggerPx": "63000.0",
    },
    {"coin": "BTC", "oid": 13, "orderType": "Limit", "isTrigger": False, "reduceOnly": False, "triggerPx": "0.0"},
    {"coin": "ETH", "oid": 14, "orderType": "Stop Market", "isTrigger": True, "reduceOnly": True, "triggerPx": "3000"},
]


def answer(statuses: list[Any]) -> Any:
    return {"status": "ok", "response": {"type": "order", "data": {"statuses": statuses}}}


@dataclass
class FakeSdk(HyperliquidSdkAdapter):
    """Stands in for the official SDK: it records the calls and answers what the test decides."""

    order_answer: Any = field(default_factory=lambda: answer([{"resting": {"oid": 4242}}]))
    cancel_answer: Any = field(default_factory=lambda: answer(["success"]))
    open_orders: Any = field(default_factory=lambda: OPEN_ORDERS)
    state: Any = field(default_factory=lambda: STATE)
    order_status: Any = field(default_factory=lambda: {"status": "order", "order": {"order": {"oid": 5151}}})
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
        return self._answer("meta", (), META)

    def all_mids(self) -> Any:
        return self._answer("all_mids", (), MIDS)

    def user_state(self, address: str) -> Any:
        return self._answer("user_state", address, self.state)

    def bulk_orders(self, requests: list[Any], grouping: str) -> Any:
        return self._answer("bulk_orders", (requests, grouping), self.order_answer)

    def cancel(self, coin: str, oid: int) -> Any:
        return self._answer("cancel", (coin, oid), self.cancel_answer)

    def frontend_open_orders(self, address: str) -> Any:
        return self._answer("frontend_open_orders", address, self.open_orders)

    def query_order_by_cloid(self, address: str, cloid: object) -> Any:
        return self._answer("query_order_by_cloid", (address, str(cloid)), self.order_status)


def adapter(sdk: FakeSdk) -> HyperliquidProtectionExchangeAdapter:
    return HyperliquidProtectionExchangeAdapter(BASE_URL, sdk)


def sent(sdk: FakeSdk) -> tuple[dict[str, Any], str]:
    [(requests_sent, grouping)] = [arguments for name, arguments in sdk.calls if name == "bulk_orders"]
    [request] = requests_sent
    return request, grouping


def test_a_stop_loss_is_a_reduce_only_trigger_at_the_market_over_the_whole_position() -> None:
    sdk = FakeSdk()

    order_id = adapter(sdk).place(ACCESS, STOP)

    request, grouping = sent(sdk)
    assert order_id == "4242"
    assert grouping == "positionTpsl"
    assert (request["coin"], request["is_buy"], request["sz"], request["reduce_only"]) == ("BTC", False, 0.0003, True)
    assert request["order_type"] == {"trigger": {"triggerPx": 57000.0, "isMarket": True, "tpsl": "sl"}}
    assert request["limit_px"] == 51300.0
    assert str(request["cloid"]) == STOP.client_order_id.hex
    assert ("exchange", (WALLET.address, BASE_URL, ADDRESS, TIMEOUT_SECONDS)) in sdk.calls


def test_a_take_profit_of_a_short_buys_with_its_limit_above_the_trigger() -> None:
    sdk = FakeSdk(
        state={
            "assetPositions": [
                {"position": {"coin": "BTC", "szi": "-0.0003", "entryPx": "60000", "leverage": {"value": 2}}}
            ]
        }
    )
    take_profit = ProtectionOrder("BTC", ProtectionKind.TAKE_PROFIT, Direction.SHORT, Decimal(54000))

    adapter(sdk).place(ACCESS, take_profit)

    request, _ = sent(sdk)
    assert (request["is_buy"], request["limit_px"]) == (True, 59400.0)
    assert request["order_type"]["trigger"]["tpsl"] == "tp"


def test_a_protection_accepted_without_its_identifier_is_looked_up_by_client_order_id() -> None:
    sdk = FakeSdk(order_answer=answer(["waitingForTrigger"]))

    assert adapter(sdk).place(ACCESS, STOP) == "5151"
    assert ("query_order_by_cloid", (ADDRESS, STOP.client_order_id.hex)) in sdk.calls


def test_a_protection_refused_by_the_exchange_keeps_its_message() -> None:
    sdk = FakeSdk(order_answer=answer([{"error": "Trigger rejected"}]))

    with pytest.raises(ExchangeRejectedOrderError) as refused:
        adapter(sdk).place(ACCESS, STOP)

    assert refused.value.exchange_message == "Trigger rejected"


def test_without_a_position_nothing_is_sent() -> None:
    sdk = FakeSdk(state={"assetPositions": []})

    with pytest.raises(ExchangeRejectedOrderError):
        adapter(sdk).place(ACCESS, STOP)

    assert not [name for name, _ in sdk.calls if name == "bulk_orders"]


@pytest.mark.parametrize(
    "answer_of_the_exchange",
    [
        {"status": "ok", "response": {"type": "order"}},
        {"status": "ok", "response": {"type": "order", "data": {"statuses": [{"resting": {"id": 1}}]}}},
        {"status": "ok", "response": {"type": "order", "data": {"statuses": []}}},
    ],
)
def test_an_answer_of_unexpected_shape_is_an_exchange_not_available_or_a_lookup(answer_of_the_exchange: Any) -> None:
    sdk = FakeSdk(order_answer=answer_of_the_exchange, order_status={"status": "unknownOid"})

    with pytest.raises(OrderExchangeUnavailableError):
        adapter(sdk).place(ACCESS, STOP)


def test_a_protection_is_cancelled_by_its_identifier() -> None:
    sdk = FakeSdk()

    adapter(sdk).cancel(ACCESS, "BTC", "4242")

    assert ("cancel", ("BTC", 4242)) in sdk.calls


def test_a_protection_the_exchange_no_longer_has_is_refused_with_its_message() -> None:
    sdk = FakeSdk(cancel_answer=answer([{"error": "Order was never placed, already canceled, or filled."}]))

    with pytest.raises(ExchangeRejectedOrderError, match="ordine rifiutato"):
        adapter(sdk).cancel(ACCESS, "BTC", "4242")


def test_the_active_protections_are_the_reduce_only_triggers_of_the_asset() -> None:
    assert adapter(FakeSdk()).active(ACCESS, "BTC") == (
        ActiveProtection("11", ProtectionKind.STOP_LOSS, Decimal("57000.0")),
        ActiveProtection("12", ProtectionKind.TAKE_PROFIT, Decimal("63000.0")),
    )


def test_open_orders_of_unexpected_shape_are_an_exchange_not_available() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        adapter(FakeSdk(open_orders=[{"coin": "BTC"}])).active(ACCESS, "BTC")


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (ClientError(400, None, "Insufficient margin", None, None), ExchangeRejectedOrderError),
        (requests.ConnectionError(), OrderExchangeUnavailableError),
    ],
)
def test_the_errors_of_the_sdk_are_those_of_the_port(failure: Exception, error: type[Exception]) -> None:
    with pytest.raises(error):
        adapter(FakeSdk(failure=failure)).active(ACCESS, "BTC")


def test_each_network_has_its_address() -> None:
    assert HyperliquidProtectionExchangeAdapter.for_network(testnet=True).base_url == TESTNET_API_URL
    assert HyperliquidProtectionExchangeAdapter.for_network(testnet=False).base_url == MAINNET_API_URL
