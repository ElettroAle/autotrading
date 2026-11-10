import re
from dataclasses import dataclass, field

from autotrading.domain.orders.errors import TradingAccessRequiredError

MASK = "***"


@dataclass(frozen=True, slots=True)
class TradingAccess:
    """What signs the orders of an account: its exchange, its address and the secret of the API wallet.

    Never shown in answers, logs or errors, so the representation masks address and secret (R0.2.3).
    """

    exchange: str
    account_address: str = field(repr=False)
    secret_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.exchange or not self.account_address or not self.secret_key:
            raise TradingAccessRequiredError

    def redact(self, text: str) -> str:
        for secret in (self.secret_key, self.account_address):
            text = re.sub(re.escape(secret), MASK, text, flags=re.IGNORECASE)
        return text

    def __repr__(self) -> str:
        return f"TradingAccess(exchange={self.exchange!r}, {MASK})"

    __str__ = __repr__
