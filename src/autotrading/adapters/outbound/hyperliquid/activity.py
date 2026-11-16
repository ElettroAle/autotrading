from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict

import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import (
    ACCOUNT_ADDRESS,
    MARGIN_CURRENCY,
    TIMEOUT_SECONDS,
    HyperliquidSdkAdapter,
)
from autotrading.adapters.outbound.hyperliquid.user_state import _UserPosition, in_account_mode, user_state_of
from autotrading.application.flows.errors import FlowCredentialsFieldMissingError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition, BalanceMovement
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_intent import TradeSide

FROM_THE_START = 0
SHAPE_ERRORS = (KeyError, TypeError, ValueError, IndexError, AttributeError, ArithmeticError)
TRANSFER_DIRECTIONS = {"deposit": TransferDirection.DEPOSIT, "withdraw": TransferDirection.WITHDRAWAL}


class _LedgerDelta(TypedDict, total=False):
    type: str
    usdc: str
    destination: str
    toPerp: bool


class _LedgerUpdate(TypedDict):
    """An update of the non-funding ledger as Hyperliquid answers it; a wrong shape fails while it is read."""

    delta: _LedgerDelta
    hash: str
    time: int


class HyperliquidAccountActivityAdapter:
    """What Hyperliquid shows of an account: positions with their margin, movements of the balance (R1.6.1), and the
    deposits and withdrawals of its history of the capital (R3.4.2, ADR storico-delle-variazioni-di-capitale).

    Everything is public information of the address: no signature, so no secret leaves the opener. The executions
    are read apart, only the new ones, for the ledger (ADR 0063). Funding payments are not movements.
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
    ) -> HyperliquidAccountActivityAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    @property
    def base_url(self) -> str:
        return self._base_url

    def reference_fields(self) -> frozenset[str]:
        return frozenset({ACCOUNT_ADDRESS})

    def activity(self, reference: AccountReference) -> AccountActivity:
        address = address_of(reference)
        with translated():
            info = self._sdk.info(self._base_url, self._timeout)
            state = in_account_mode(
                user_state_of(info.user_state(address)),
                info.query_user_abstraction_state(address),
                info.spot_user_state(address),
            )
            ledger = info.user_non_funding_ledger_updates(address, FROM_THE_START)
            return AccountActivity(
                currency=MARGIN_CURRENCY,
                balance=state.account_value,
                available_margin=state.withdrawable,
                positions=tuple(_position_of(position) for position in state.positions),
                movements=tuple(movement for update in ledger if (movement := _movement_of(update, address))),
                read_at=state.read_at,
            )

    def transfers(self, reference: AccountReference, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        address = address_of(reference)
        start = FROM_THE_START if window.since is None else _milliseconds(window.since)
        end = None if window.until is None else _milliseconds(window.until)
        with translated():
            info = self._sdk.info(self._base_url, self._timeout)
            ledger = info.user_non_funding_ledger_updates(address, start, end)
            # The exchange includes the end it is given; the window excludes it.
            transfers = (transfer for update in ledger if (transfer := _transfer_of(update)))
            return tuple(transfer for transfer in transfers if window.contains(transfer.transferred_at))


@contextmanager
def translated() -> Iterator[None]:
    # An answer of unexpected shape is a fault of the exchange, never a reason to report invented values.
    try:
        yield
    except (ClientError, ServerError, requests.RequestException, *SHAPE_ERRORS) as error:
        raise FlowExchangeUnavailableError from error


def _position_of(position: _UserPosition) -> AccountPosition:
    return AccountPosition(
        asset=position.coin,
        side=TradeSide.LONG if position.signed_size > 0 else TradeSide.SHORT,
        size=abs(position.signed_size),
        margin=position.margin,
        unrealized_pnl=position.unrealized_pnl,
        leverage=position.leverage,
        entry_price=position.entry_price,
        mark_price=position.mark_price,
    )


def _movement_of(update: _LedgerUpdate, address: str) -> BalanceMovement | None:
    delta = update["delta"]
    amount = _signed_amount(delta, address.lower())
    if amount is None:
        return None
    return BalanceMovement(str(update["hash"]), amount, _instant(update["time"]))


def _signed_amount(delta: _LedgerDelta, address: str) -> Decimal | None:
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


def _transfer_of(update: _LedgerUpdate) -> AccountTransfer | None:
    """The deposit or withdrawal a ledger update declares, or None for any other update."""
    direction = TRANSFER_DIRECTIONS.get(update["delta"]["type"])
    if direction is None:
        return None
    return AccountTransfer(_instant(update["time"]), _decimal(update["delta"]["usdc"]), direction)


def _milliseconds(instant: datetime) -> int:
    return int(instant.timestamp() * 1000)


def _instant(milliseconds: int | str) -> datetime:
    return datetime.fromtimestamp(int(milliseconds) / 1000, UTC)


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def address_of(reference: AccountReference) -> str:
    """The address an account is read by; a reference without it is refused before reaching the exchange."""
    found = reference.fields.get(ACCOUNT_ADDRESS)
    if found is None:
        raise FlowCredentialsFieldMissingError
    return found
