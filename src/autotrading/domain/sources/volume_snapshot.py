from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.sources.errors import InvalidVolumeSnapshotError
from autotrading.domain.sources.volume_figures import VolumeFigures

# The imbalance weighs the orders within 1% of the mid price, on both sides (R5.1.2).
BAND = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class BookLevel:
    """A price of the order book with the quantity resting at it."""

    price: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        if self.price <= 0 or self.quantity < 0:
            raise InvalidVolumeSnapshotError

    @property
    def value(self) -> Decimal:
        return self.price * self.quantity


@dataclass(frozen=True, slots=True)
class VolumeSnapshot:
    """The market data of an asset on an exchange, as the exchange publishes it: the volume of the last 24 hours in
    dollars, the aggressive buys and sells of the interval of the cycle in dollars and the order book (R5.1.2, ADR
    fonte-volumi-con-adapter-binance)."""

    volume_24h_usd: Decimal
    taker_buy: Decimal
    taker_sell: Decimal
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]

    def __post_init__(self) -> None:
        if min(self.volume_24h_usd, self.taker_buy, self.taker_sell) < 0:
            raise InvalidVolumeSnapshotError

    @property
    def taker_ratio(self) -> Decimal | None:
        """The aggressive buys over the aggressive sells; None without aggressive sells."""
        if self.taker_sell == 0:
            return None
        return self.taker_buy / self.taker_sell

    @property
    def book_imbalance(self) -> Decimal | None:
        """The value of the bids within 1% below the mid price over the value of the bids and asks within 1% of it;
        None when the book has no side or no value within the band."""
        if not self.bids or not self.asks:
            return None
        mid = (max(level.price for level in self.bids) + min(level.price for level in self.asks)) / 2
        bids = sum((level.value for level in self.bids if level.price >= mid * (1 - BAND)), Decimal(0))
        asks = sum((level.value for level in self.asks if level.price <= mid * (1 + BAND)), Decimal(0))
        if bids + asks == 0:
            return None
        return bids / (bids + asks)

    def figures(self) -> VolumeFigures:
        return VolumeFigures(self.volume_24h_usd, self.taker_ratio, self.book_imbalance)


@dataclass(frozen=True, slots=True)
class UnlistedAsset:
    """The exchange of the adapter does not list the asset: a declared value, not an error (R5.1.2)."""

    asset: str
