from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.sources.errors import InvalidWhaleTransferError

UNLABELLED = "indirizzo non etichettato"


@dataclass(frozen=True, slots=True)
class WhaleTransfer:
    """A transfer of a crypto asset as its provider recorded it on chain, with its value in dollars at that instant and
    what is known of the two ends (R5.1.1)."""

    at: datetime
    asset: str
    quantity: Decimal
    usd_value: Decimal
    origin: str | None
    destination: str | None

    def __post_init__(self) -> None:
        if self.at.tzinfo is None or not self.asset.strip() or self.quantity <= 0 or self.usd_value < 0:
            raise InvalidWhaleTransferError

    @property
    def description(self) -> str | None:
        """Where the transfer comes from and goes to, when at least one end is known (R5.1.1)."""
        if self.origin is None and self.destination is None:
            return None
        return f"da {self.origin or UNLABELLED} a {self.destination or UNLABELLED}"


def large_transfers(transfers: Iterable[WhaleTransfer], minimum_usd: int) -> tuple[WhaleTransfer, ...]:
    """The transfers at or above the threshold of value, newest first (R5.1.1)."""
    large = (transfer for transfer in transfers if transfer.usd_value >= minimum_usd)
    return tuple(sorted(large, key=lambda transfer: transfer.at, reverse=True))
