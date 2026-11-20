from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

VOLUME_24H = "volume_24h_usd"
TAKER_RATIO = "rapporto_taker_buy_sell"
BOOK_IMBALANCE = "squilibrio_order_book_1_percento"
NOTE = "nota"
DOLLAR = Decimal(1)
RATIO = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class VolumeFigures:
    """What the agent reads of the volumes of an asset on an exchange, or on several together (R5.1.2): the volume of
    the last 24 hours in dollars, the aggressive buys over the aggressive sells and the share of the bids within 1% of
    the price; a ratio is None when it cannot be measured.
    """

    volume_24h_usd: Decimal
    taker_ratio: Decimal | None
    book_imbalance: Decimal | None

    def values(self) -> dict[str, str]:
        """The volume to the dollar and the ratios to four decimals, a ratio not known left out."""
        values = {VOLUME_24H: _plain(self.volume_24h_usd, DOLLAR)}
        if self.taker_ratio is not None:
            values[TAKER_RATIO] = _plain(self.taker_ratio, RATIO)
        if self.book_imbalance is not None:
            values[BOOK_IMBALANCE] = _plain(self.book_imbalance, RATIO)
        return values

    @classmethod
    def of_values(cls, values: Mapping[str, str]) -> VolumeFigures | None:
        """The figures the values carry; None for the note of an asset not listed."""
        volume = values.get(VOLUME_24H)
        if volume is None:
            return None
        return cls(
            Decimal(volume), _decimal_or_none(values.get(TAKER_RATIO)), _decimal_or_none(values.get(BOOK_IMBALANCE))
        )


def unlisted_note(adapter: str) -> dict[str, str]:
    """An asset the exchange of the adapter does not list is a datum, not an absent source (R5.1.2)."""
    return {NOTE: f"non quotato su {adapter}"}


def volume_weighted(figures: Sequence[VolumeFigures]) -> VolumeFigures:
    """The figures of several exchanges together: the volumes summed, every ratio weighted on the volume of the
    exchanges that measure it (R5.1.2)."""
    return VolumeFigures(
        sum((figure.volume_24h_usd for figure in figures), Decimal(0)),
        _weighted(figures, lambda figure: figure.taker_ratio),
        _weighted(figures, lambda figure: figure.book_imbalance),
    )


def _weighted(figures: Sequence[VolumeFigures], ratio_of: Callable[[VolumeFigures], Decimal | None]) -> Decimal | None:
    measured = [(ratio, figure.volume_24h_usd) for figure in figures if (ratio := ratio_of(figure)) is not None]
    volume = sum((weight for _, weight in measured), Decimal(0))
    if volume == 0:
        return None
    return sum((ratio * weight for ratio, weight in measured), Decimal(0)) / volume


def _decimal_or_none(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


def _plain(amount: Decimal, step: Decimal) -> str:
    return format(amount.quantize(step), "f")
