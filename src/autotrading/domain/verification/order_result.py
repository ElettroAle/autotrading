from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderResult:
    """What an order of the procedure did: executed or not, its fee, its realized result and why it failed."""

    succeeded: bool
    fee: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    message: str | None = None

    @classmethod
    def reported(
        cls, fee: Decimal | None, realized_pnl: Decimal | None, exchange_message: str | None, status: str
    ) -> OrderResult:
        """An order is succeeded when the exchange executed it; otherwise it says why the exchange refused it, or
        its status when the exchange gave no reason (an order without outcome)."""
        if fee is None or realized_pnl is None:
            return cls(succeeded=False, message=status if exchange_message is None else exchange_message)
        return cls(succeeded=True, fee=fee, realized_pnl=realized_pnl)
