from dataclasses import dataclass
from decimal import Decimal

ROUND_TRIP_COST = "costo di andata e ritorno"
# One market order opens the position and one closes it.
ORDERS_OF_A_ROUND_TRIP = 2
PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class RoundTripCost:
    """What a cycle read of the fee the exchange applies to the account of its flow for a market order (R5.5.6, ADR
    costo-di-andata-e-ritorno-nel-contesto-dell-agente): nothing with the option of the flow off, the rate when the
    exchange gave it, the reason when it did not.

    The cost is the fee counted for the opening and for the closing, in percent of the value of the position; a fee
    not read is a missing datum of the cycle, never its failure.
    """

    # A share of the value of the order, as the exchange gives it.
    market_order_fee_rate: Decimal | None = None
    unread_reason: str | None = None

    @classmethod
    def of_rate(cls, rate: Decimal) -> RoundTripCost:
        return cls(market_order_fee_rate=rate)

    @classmethod
    def unread(cls, reason: str) -> RoundTripCost:
        return cls(unread_reason=reason)

    @property
    def percent(self) -> Decimal | None:
        rate = self.market_order_fee_rate
        if rate is None:
            return None
        return _plain(rate * ORDERS_OF_A_ROUND_TRIP * PERCENT)

    @property
    def missing(self) -> tuple[str, ...]:
        if self.unread_reason is None:
            return ()
        return (f"{ROUND_TRIP_COST}: {self.unread_reason}",)


def _plain(value: Decimal) -> Decimal:
    """The same value without trailing zeros and without an exponent, as a person writes it."""
    return Decimal(format(value.normalize(), "f"))
