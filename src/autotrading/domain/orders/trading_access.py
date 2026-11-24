import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from autotrading.domain.orders.errors import TradingAccessRequiredError

MASK = "***"


@dataclass(frozen=True, slots=True)
class TradingAccess:
    """What signs the orders of an account: its exchange and the opened fields, by the names the exchange declares.

    Only the adapter of the exchange knows which field is which (ADR 0158, Bug 284). Never shown in answers, logs or
    errors, so the representation masks every field (R0.2.3). An account of an exchange without credentials is reached
    by its identifier alone, which the exchange keeps the account by (R6.3.2).
    """

    exchange: str
    fields: Mapping[str, str] = field(repr=False)
    account_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.exchange or not all(value.strip() for value in self.fields.values()):
            raise TradingAccessRequiredError
        if not self.fields and self.account_id is None:
            raise TradingAccessRequiredError
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    @classmethod
    def without_credentials(cls, exchange: str, account_id: UUID) -> TradingAccess:
        return cls(exchange, {}, account_id)

    def value(self, name: str) -> str:
        found = self.fields.get(name)
        if found is None:
            raise TradingAccessRequiredError
        return found

    def redact(self, text: str) -> str:
        for secret in sorted(self.fields.values(), key=len, reverse=True):
            text = re.sub(re.escape(secret), MASK, text, flags=re.IGNORECASE)
        return text

    def __hash__(self) -> int:
        return hash((self.exchange, frozenset(self.fields.items()), self.account_id))

    def __repr__(self) -> str:
        return f"TradingAccess(exchange={self.exchange!r}, {MASK})"

    __str__ = __repr__
