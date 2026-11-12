from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import (
    MARGIN_CURRENCY,
    TIMEOUT_SECONDS,
    HyperliquidSdk,
    OfficialSdk,
)
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition, BalanceMovement
from autotrading.domain.flows.trade_intent import TradeSide

FROM_THE_START = 0
SHAPE_ERRORS = (KeyError, TypeError, ValueError, IndexError, AttributeError, InvalidOperation)


class HyperliquidAccountActivityAdapter:
    """What Hyperliquid shows of an account: positions with their margin, movements of the balance (R1.6.1).

    Everything is public information of the address: no signature, so no secret leaves the opener. The executions
    are read apart, only the new ones, for the ledger (ADR 0063). Funding payments are not movements.
    """

    def __init__(self, base_url: str, sdk: HyperliquidSdk | None = None, timeout: float = TIMEOUT_SECONDS) -> None:
        self._base_url = base_url
        self._sdk = sdk or OfficialSdk()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdk | None = None) -> HyperliquidAccountActivityAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    @property
    def base_url(self) -> str:
        return self._base_url

    def activity(self, address: str) -> AccountActivity:
        with translated():
            info = self._sdk.info(self._base_url, self._timeout)
            state = info.user_state(address)
            ledger = info.user_non_funding_ledger_updates(address, FROM_THE_START)
            return AccountActivity(
                currency=MARGIN_CURRENCY,
                balance=_decimal(state["marginSummary"]["accountValue"]),
                available_margin=_decimal(state["withdrawable"]),
                positions=tuple(_position_of(entry["position"]) for entry in state["assetPositions"]),
                movements=tuple(movement for update in ledger if (movement := _movement_of(update, address))),
                read_at=_instant(state["time"]),
            )


@contextmanager
def translated() -> Iterator[None]:
    # An answer of unexpected shape is a fault of the exchange, never a reason to report invented values.
    try:
        yield
    except (ClientError, ServerError, requests.RequestException, *SHAPE_ERRORS) as error:
        raise FlowExchangeUnavailableError from error


def _position_of(position: Mapping[str, Any]) -> AccountPosition:
    size = _decimal(position["szi"])
    return AccountPosition(
        asset=str(position["coin"]),
        side=TradeSide.LONG if size > 0 else TradeSide.SHORT,
        size=abs(size),
        margin=_decimal(position["marginUsed"]),
        unrealized_pnl=_decimal(position["unrealizedPnl"]),
    )


def _movement_of(update: Mapping[str, Any], address: str) -> BalanceMovement | None:
    delta = update["delta"]
    amount = _signed_amount(delta, address.lower())
    if amount is None:
        return None
    return BalanceMovement(str(update["hash"]), amount, _instant(update["time"]))


def _signed_amount(delta: Mapping[str, Any], address: str) -> Decimal | None:
    """The change of the perpetual balance a ledger update makes, or None for one that is not a movement."""
    kind = delta["type"]
    if kind == "deposit":
        return _decimal(delta["usdc"])
    if kind == "withdraw":
        return -_decimal(delta["usdc"])
    if kind in {"internalTransfer", "subAccountTransfer"}:
        incoming = str(delta["destination"]).lower() == address
        return _decimal(delta["usdc"]) if incoming else -_decimal(delta["usdc"])
    if kind == "accountClassTransfer":
        return _decimal(delta["usdc"]) if delta["toPerp"] else -_decimal(delta["usdc"])
    return None


def _instant(milliseconds: Any) -> datetime:
    return datetime.fromtimestamp(int(milliseconds) / 1000, UTC)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))
