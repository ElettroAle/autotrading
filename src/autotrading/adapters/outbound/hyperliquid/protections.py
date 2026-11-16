from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import TypedDict, cast

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.signing import OrderRequest
from hyperliquid.utils.types import Cloid

from autotrading.adapters.outbound.hyperliquid.exchange import ACCOUNT_ADDRESS, TIMEOUT_SECONDS, HyperliquidSdkAdapter
from autotrading.adapters.outbound.hyperliquid.orders import (
    SHAPE_ERRORS,
    _decimal,
    _field,
    _held_position_of,
    _market_of,
    _require_ok,
    _translated,
    _wallet_of,
)
from autotrading.application.orders.errors import ExchangeRejectedOrderError, OrderExchangeUnavailableError
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ActiveProtection, ProtectionOrder
from autotrading.domain.orders.trading_access import TradingAccess

# A protection executes at the market once its price is reached: the limit only bounds how far the fill may go, as wide
# as the exchange itself sets it for the protections of its own interface.
TRIGGER_SLIPPAGE = Decimal("0.1")
TPSL_OF = {ProtectionKind.STOP_LOSS: "sl", ProtectionKind.TAKE_PROFIT: "tp"}
# The order types Hyperliquid shows for the protections waiting for their price.
KIND_OF_ORDER_TYPE = {
    "Stop Market": ProtectionKind.STOP_LOSS,
    "Stop Limit": ProtectionKind.STOP_LOSS,
    "Take Profit Market": ProtectionKind.TAKE_PROFIT,
    "Take Profit Limit": ProtectionKind.TAKE_PROFIT,
}
NO_POSITION = "nessuna posizione da proteggere"


class _OpenOrder(TypedDict):
    """An order waiting on the exchange, as the frontend open orders give it; a wrong shape fails while it is read."""

    coin: str
    oid: int
    orderType: str
    isTrigger: bool
    reduceOnly: bool
    triggerPx: str


class HyperliquidProtectionExchangeAdapter:
    """Stop loss and take profit on Hyperliquid with the official SDK: trigger orders at the market, reduce only, in the
    `positionTpsl` grouping that ties them to the whole position (R3.1.2, ADR ordini-di-protezione-sull-exchange).

    Each carries the `cloid` the platform gave it, so its execution belongs to the flow. No retries.
    """

    def __init__(
        self, base_url: str, sdk: HyperliquidSdkAdapter | None = None, timeout: float = TIMEOUT_SECONDS
    ) -> None:
        self._base_url = base_url
        self._sdk = sdk or HyperliquidSdkAdapter()
        self._timeout = timeout

    @classmethod
    def for_network(
        cls, *, testnet: bool, sdk: HyperliquidSdkAdapter | None = None
    ) -> HyperliquidProtectionExchangeAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    @property
    def base_url(self) -> str:
        return self._base_url

    def place(self, access: TradingAccess, order: ProtectionOrder) -> str:
        request = self._request(access, order)
        with _translated(access):
            response = self._exchange(access).bulk_orders([request], grouping="positionTpsl")
        oid = _placed_oid(response, access)
        return str(oid) if oid is not None else self._oid_by_cloid(access, order)

    def cancel(self, access: TradingAccess, asset: str, order_id: str) -> None:
        with _translated(access):
            response = self._exchange(access).cancel(asset, int(order_id))
        _require_success(response, access)

    def active(self, access: TradingAccess, asset: str) -> tuple[ActiveProtection, ...]:
        with _translated(access):
            orders = self._sdk.info(self._base_url, self._timeout).frontend_open_orders(_field(access, ACCOUNT_ADDRESS))
        return _protections_of(orders, asset)

    def _request(self, access: TradingAccess, order: ProtectionOrder) -> OrderRequest:
        with _translated(access):
            info = self._sdk.info(self._base_url, self._timeout)
            state = info.user_state(_field(access, ACCOUNT_ADDRESS))
            universe, mids = info.meta()["universe"], info.all_mids()
        position = _held_position_of(state, order.asset)
        if position is None:
            raise ExchangeRejectedOrderError(NO_POSITION)
        market = _market_of(order.asset, universe, mids)
        slippage = TRIGGER_SLIPPAGE if order.is_buy else -TRIGGER_SLIPPAGE
        limit = market.rounded_price(order.trigger_price * (1 + slippage))
        return {
            "coin": order.asset,
            "is_buy": order.is_buy,
            "sz": float(position.size),
            "limit_px": float(limit),
            "order_type": {
                "trigger": {"triggerPx": float(order.trigger_price), "isMarket": True, "tpsl": TPSL_OF[order.kind]}
            },
            "reduce_only": True,
            "cloid": Cloid.from_str(order.client_order_id.hex),
        }

    def _oid_by_cloid(self, access: TradingAccess, order: ProtectionOrder) -> str:
        """A protection accepted to wait for its price without its identifier in the answer is looked up by `cloid`."""
        with _translated(access):
            status = self._sdk.info(self._base_url, self._timeout).query_order_by_cloid(
                _field(access, ACCOUNT_ADDRESS), Cloid.from_str(order.client_order_id.hex)
            )
        try:
            return str(int(cast("Mapping[str, Mapping[str, Mapping[str, int]]]", status)["order"]["order"]["oid"]))
        except SHAPE_ERRORS as error:
            raise OrderExchangeUnavailableError from error

    def _exchange(self, access: TradingAccess) -> Exchange:
        return self._sdk.exchange(_wallet_of(access), self._base_url, _field(access, ACCOUNT_ADDRESS), self._timeout)


def _statuses(response: object, access: TradingAccess) -> list[object]:
    _require_ok(response, access)
    try:
        return list(
            cast("Mapping[str, Mapping[str, Mapping[str, list[object]]]]", response)["response"]["data"]["statuses"]
        )
    except SHAPE_ERRORS as error:
        raise OrderExchangeUnavailableError from error


def _placed_oid(response: object, access: TradingAccess) -> int | None:
    statuses = _statuses(response, access)
    status = statuses[0] if statuses else None
    if not isinstance(status, Mapping):
        # Accepted to wait for the price ("waitingForTrigger"), without its identifier.
        return None
    if "error" in status:
        raise ExchangeRejectedOrderError(access.redact(str(status["error"])))
    placed = status.get("resting") or status.get("filled")
    if not isinstance(placed, Mapping) or "oid" not in placed:
        return None
    return int(str(placed["oid"]))


def _require_success(response: object, access: TradingAccess) -> None:
    for status in _statuses(response, access):
        if isinstance(status, Mapping) and "error" in status:
            raise ExchangeRejectedOrderError(access.redact(str(status["error"])))


def _protections_of(answer: object, asset: str) -> tuple[ActiveProtection, ...]:
    orders = cast("Sequence[_OpenOrder]", answer)
    try:
        return tuple(
            ActiveProtection(str(order["oid"]), KIND_OF_ORDER_TYPE[order["orderType"]], _decimal(order["triggerPx"]))
            for order in orders
            if order["coin"] == asset
            and order["isTrigger"]
            and order["reduceOnly"]
            and order["orderType"] in KIND_OF_ORDER_TYPE
        )
    except SHAPE_ERRORS as error:
        raise OrderExchangeUnavailableError from error
