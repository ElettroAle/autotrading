from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import NotRequired, TypedDict, cast
from uuid import UUID

from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from autotrading.adapters.outbound.hyperliquid.activity import translated
from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS, HyperliquidSdkAdapter
from autotrading.domain.flows.ledger import Execution, ExecutionsWindow, FundingPayment

# The exchange answers at most 2000 fills and 500 funding payments per request, and keeps only the 10000 most recent
# fills of an account: reading that many since a moment means older ones may be gone already.
FILLS_PAGE = 2000
FUNDING_PAGE = 500
FILLS_KEPT = 10000
FROM_THE_START = 0
PURCHASE = "B"

type Page = list[Mapping[str, object]]


class _Fill(TypedDict):
    """A fill as Hyperliquid answers it; a wrong shape fails while it is read."""

    tid: int
    oid: int
    cloid: NotRequired[str | None]
    coin: str
    side: str
    sz: str
    px: str
    fee: str
    closedPnl: str
    startPosition: str
    liquidation: NotRequired[object]
    time: int


class _FundingDelta(TypedDict):
    coin: str
    usdc: str


class _FundingPayment(TypedDict):
    delta: _FundingDelta
    time: int


class HyperliquidAccountExecutionsAdapter:
    """The executions and funding payments of an address since a moment, for the ledger of the flows (ADR 0063).

    Public information of the address: no signature. Only what is newer than the moment travels, page by page.
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
    ) -> HyperliquidAccountExecutionsAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    @property
    def base_url(self) -> str:
        return self._base_url

    def since(self, address: str, since: datetime | None) -> ExecutionsWindow:
        start = FROM_THE_START if since is None else int(since.timestamp() * 1000)
        with translated():
            info = self._sdk.info(self._base_url, self._timeout)
            fills = _pages(lambda moment: info.user_fills_by_time(address, moment), start, FILLS_PAGE)
            funding = _pages(lambda moment: info.user_funding_history(address, moment), start, FUNDING_PAGE)
            return ExecutionsWindow(
                executions=tuple(_execution_of(fill) for fill in fills),
                funding=tuple(_payment_of(payment) for payment in funding),
                # From the start, what the exchange keeps is the starting point; since a moment, a full history
                # means the oldest executions after that moment may be gone.
                complete=since is None or len(fills) < FILLS_KEPT,
            )


def _pages(read: Callable[[int], Page], start: int, page_size: int) -> Page:
    items: Page = []
    moment = start
    while True:
        page = read(moment)
        items.extend(page)
        if len(page) < page_size:
            return items
        moment = int(str(page[-1]["time"])) + 1


def _execution_of(entry: Mapping[str, object]) -> Execution:
    fill = cast("_Fill", entry)
    cloid = fill.get("cloid")
    size = _decimal(fill["sz"])
    return Execution(
        fill_id=str(fill["tid"]),
        exchange_order_id=str(fill["oid"]),
        order_id=None if cloid is None else UUID(hex=str(cloid).removeprefix("0x")),
        asset=str(fill["coin"]),
        size=size if fill["side"] == PURCHASE else -size,
        price=_decimal(fill["px"]),
        fee=_decimal(fill["fee"]),
        realized_pnl=_decimal(fill["closedPnl"]),
        start_position=_decimal(fill["startPosition"]),
        liquidation=fill.get("liquidation") is not None,
        executed_at=_instant(fill["time"]),
    )


def _payment_of(entry: Mapping[str, object]) -> FundingPayment:
    payment = cast("_FundingPayment", entry)
    delta = payment["delta"]
    return FundingPayment(str(delta["coin"]), _decimal(delta["usdc"]), _instant(payment["time"]))


def _instant(milliseconds: int | str) -> datetime:
    return datetime.fromtimestamp(int(milliseconds) / 1000, UTC)


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))
