from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class ExpirySource(StrEnum):
    """Who gave the day a key stops working, the same names for every key (R6.2.2)."""

    READ = "read"
    ENTERED = "entered"


class ExpiryStatus(StrEnum):
    """The state of the expiry of a key as of today, the same names for every key (R6.2.2)."""

    UNKNOWN = "unknown"
    VALID = "valid"
    EXPIRING = "expiring"
    EXPIRED = "expired"


class KeyExpiryResponse(BaseModel):
    """The day a key stops working, in UTC, and who gave it: `read` by the adapter, `entered` by the user (R6.2.2)."""

    expires_on: date
    source: ExpirySource

    @classmethod
    def of(cls, expires_on: date, source: StrEnum) -> KeyExpiryResponse:
        return cls(expires_on=expires_on, source=ExpirySource(source.value))


class KeyExpiryRequest(BaseModel):
    """The day the user says a key stops working; none forgets it (R6.2.2)."""

    expires_on: date | None = None
