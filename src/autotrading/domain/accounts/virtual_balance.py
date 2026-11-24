from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.accounts.errors import InvalidVirtualBalanceError, VirtualBalanceRequiredError


@dataclass(frozen=True, slots=True)
class VirtualBalance:
    """The balance an account of the simulated exchange starts from, or is reset to, as the user gives it (R6.3.2)."""

    amount: Decimal

    def __post_init__(self) -> None:
        if not self.amount.is_finite() or self.amount <= 0:
            raise InvalidVirtualBalanceError(self.amount)

    @classmethod
    def required(cls, amount: Decimal | None) -> VirtualBalance:
        if amount is None:
            raise VirtualBalanceRequiredError
        return cls(amount)
