from dataclasses import dataclass
from enum import StrEnum


class RejectionReason(StrEnum):
    BELOW_MINIMUM = "importo sotto il minimo"
    INSUFFICIENT_MARGIN = "margine insufficiente"
    UNKNOWN_ASSET = "asset non disponibile"
    PRICE_BEYOND_SLIPPAGE = "prezzo oltre lo scostamento massimo"
    OTHER = "rifiuto dell'exchange"


# A market order is an IOC limit at the slipped price: when no resting order is within it, nothing matches.
_REASONS = (
    ("minimum value", RejectionReason.BELOW_MINIMUM),
    ("insufficient margin", RejectionReason.INSUFFICIENT_MARGIN),
    ("unknown asset", RejectionReason.UNKNOWN_ASSET),
    ("could not immediately match", RejectionReason.PRICE_BEYOND_SLIPPAGE),
)


@dataclass(frozen=True, slots=True)
class Rejection:
    """A refusal of the exchange: a reason the user reads and the original message, always kept (R0.3.3)."""

    reason: RejectionReason
    exchange_message: str

    @classmethod
    def of(cls, exchange_message: str) -> Rejection:
        text = exchange_message.lower()
        reason = next((reason for fragment, reason in _REASONS if fragment in text), RejectionReason.OTHER)
        return cls(reason, exchange_message)
