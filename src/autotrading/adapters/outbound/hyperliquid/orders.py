from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import requests
from eth_account import Account as EthereumAccount
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError
from hyperliquid.utils.types import Cloid

from autotrading.adapters.outbound.hyperliquid.exchange import (
    INVALID_KEY_MESSAGE,
    TIMEOUT_SECONDS,
    HyperliquidSdk,
    OfficialSdk,
)
from autotrading.application.orders.errors import (
    ExchangeRejectedOrderError,
    OrderExchangeUnavailableError,
    OrderNotAcknowledgedError,
)
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess

UNKNOWN_ASSET = "Unknown asset"
SHAPE_ERRORS = (KeyError, TypeError, ValueError, IndexError, ArithmeticError)


class HyperliquidOrderExchangeAdapter:
    """Orders on Hyperliquid with the official SDK: market orders within the slippage, each with its `cloid`.

    The outcome is computed from the fills of the order, never from what was asked (R0.3.4). No retries: an order
    the exchange does not confirm in 10 seconds is reported as not acknowledged, and looked up by `cloid` (R0.3.3).
    """

    def __init__(self, base_url: str, sdk: HyperliquidSdk | None = None, timeout: float = TIMEOUT_SECONDS) -> None:
        self._base_url = base_url
        self._sdk = sdk or OfficialSdk()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdk | None = None) -> HyperliquidOrderExchangeAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    def market(self, access: TradingAccess, coin: str) -> Market:
        with _translated(access):
            info = self._sdk.info(self._base_url, self._timeout)
            universe, mids = info.meta()["universe"], info.all_mids()
        return _market_of(coin, universe, mids)

    def set_leverage(self, access: TradingAccess, coin: str, leverage: int) -> None:
        with _translated(access):
            response = self._exchange(access).update_leverage(leverage, coin, True)
        _require_ok(response, access)

    def place_market_order(self, access: TradingAccess, order: MarketOrder) -> Execution:
        with _translated(access, on_timeout=OrderNotAcknowledgedError):
            response = self._send(self._exchange(access), order)
        execution = self._execution(access, _filled_oid(response, access))
        if execution is None:
            # Filled but without fills yet: the outcome is not confirmed, so it is looked up like a silent order.
            raise OrderNotAcknowledgedError
        return execution

    def find_order(self, access: TradingAccess, order: MarketOrder) -> Execution | None:
        with _translated(access):
            status = self._sdk.info(self._base_url, self._timeout).query_order_by_cloid(
                access.account_address, _cloid_of(order)
            )
        oid = _oid_of(status)
        return None if oid is None else self._execution(access, oid)

    def _exchange(self, access: TradingAccess) -> Any:
        return self._sdk.exchange(_wallet_of(access), self._base_url, access.account_address, self._timeout)

    @staticmethod
    def _send(exchange: Any, order: MarketOrder) -> Any:
        size, slippage, cloid = float(order.size), float(order.slippage.fraction), _cloid_of(order)
        if order.reduce_only:
            return exchange.market_close(order.coin, size, None, slippage, cloid)
        return exchange.market_open(order.coin, order.is_buy, size, None, slippage, cloid)

    def _execution(self, access: TradingAccess, oid: int) -> Execution | None:
        with _translated(access):
            fills = self._sdk.info(self._base_url, self._timeout).user_fills(access.account_address)
        return _execution_of(fills, oid)


@contextmanager
def _translated(access: TradingAccess, on_timeout: type[Exception] = OrderExchangeUnavailableError) -> Iterator[None]:
    # No exception of the SDK or of the network leaves the adapter (rule layer-adapters).
    try:
        yield
    except ClientError as error:
        raise ExchangeRejectedOrderError(access.redact(str(error.error_message))) from error
    except requests.Timeout as error:
        raise on_timeout from error
    except (ServerError, requests.RequestException) as error:
        raise OrderExchangeUnavailableError from error


def _wallet_of(access: TradingAccess) -> LocalAccount:
    try:
        wallet: LocalAccount = EthereumAccount.from_key(access.secret_key)
    except ValueError as error:
        raise ExchangeRejectedOrderError(INVALID_KEY_MESSAGE) from error
    return wallet


def _cloid_of(order: MarketOrder) -> Cloid:
    return Cloid.from_str(order.id.hex)


def _market_of(coin: str, universe: Sequence[Mapping[str, Any]], mids: Mapping[str, Any]) -> Market:
    asset = next((asset for asset in universe if asset.get("name") == coin), None)
    if asset is None or coin not in mids:
        message = f"{UNKNOWN_ASSET} {coin}"
        raise ExchangeRejectedOrderError(message)
    try:
        return Market(coin, int(asset["maxLeverage"]), int(asset["szDecimals"]), _decimal(mids[coin]))
    except SHAPE_ERRORS as error:
        raise OrderExchangeUnavailableError from error


def _require_ok(response: Any, access: TradingAccess) -> None:
    if isinstance(response, Mapping) and response.get("status") == "ok":
        return
    message = response.get("response") if isinstance(response, Mapping) else response
    raise ExchangeRejectedOrderError(access.redact(str(message)))


def _filled_oid(response: Any, access: TradingAccess) -> int:
    _require_ok(response, access)
    try:
        status = response["response"]["data"]["statuses"][0]
        if "error" in status:
            raise ExchangeRejectedOrderError(access.redact(str(status["error"])))
        return int(status["filled"]["oid"])
    except SHAPE_ERRORS as error:
        # A market order is immediate or cancel: it never rests, so any other answer is not one we understand.
        raise OrderExchangeUnavailableError from error


def _oid_of(status: Any) -> int | None:
    try:
        if status["status"] != "order":
            return None
        return int(status["order"]["order"]["oid"])
    except SHAPE_ERRORS as error:
        raise OrderExchangeUnavailableError from error


def _execution_of(fills: Any, oid: int) -> Execution | None:
    try:
        own = [fill for fill in fills if int(fill["oid"]) == oid]
        if not own:
            return None
        size = sum((_decimal(fill["sz"]) for fill in own), Decimal(0))
        return Execution(
            filled_size=size,
            average_price=sum((_decimal(fill["px"]) * _decimal(fill["sz"]) for fill in own), Decimal(0)) / size,
            fee=sum((_decimal(fill["fee"]) for fill in own), Decimal(0)),
            realized_pnl=sum((_decimal(fill["closedPnl"]) for fill in own), Decimal(0)),
            executed_at=datetime.fromtimestamp(max(int(fill["time"]) for fill in own) / 1000, UTC),
        )
    except SHAPE_ERRORS as error:
        raise OrderExchangeUnavailableError from error


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))
