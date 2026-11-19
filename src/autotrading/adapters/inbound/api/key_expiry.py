from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class KeyExpiryResponse(BaseModel):
    """The day a key stops working, in UTC, and who gave it: `read` by the adapter, `entered` by the user (R6.2.2)."""

    expires_on: date
    source: str

    @classmethod
    def of(cls, expires_on: date, source: StrEnum) -> KeyExpiryResponse:
        return cls(expires_on=expires_on, source=source.value)


class KeyExpiryRequest(BaseModel):
    """The day the user says a key stops working; none forgets it (R6.2.2)."""

    expires_on: date | None = None
