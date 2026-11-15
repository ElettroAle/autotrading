import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from autotrading.domain.orders.errors import TradingAccessRequiredError

MASK = "***"


@dataclass(frozen=True, slots=True)
class TradingAccess:
    """What signs the orders of an account: its exchange and the opened fields, by the names the exchange declares.

    Only the adapter of the exchange knows which field is which (ADR 0158, Bug 284). Never shown in answers, logs or
    errors, so the representation masks every field (R0.2.3).
    """

    exchange: str
    fields: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not self.exchange or not self.fields or not all(value.strip() for value in self.fields.values()):
            raise TradingAccessRequiredError
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

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
        return hash((self.exchange, frozenset(self.fields.items())))

    def __repr__(self) -> str:
        return f"TradingAccess(exchange={self.exchange!r}, {MASK})"

    __str__ = __repr__
