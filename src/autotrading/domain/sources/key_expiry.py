from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

# Credentials expiring within these days, or already expired, is shown with a warning until it is renewed (R6.2.2).
EXPIRING_WITHIN_DAYS = 30


class KeyExpirySource(StrEnum):
    """Who gave the date: the adapter of the source, when it reads it, or the user (R6.2.2, R4.1.2)."""

    READ = "read"
    ENTERED = "entered"


class KeyExpiryStatus(StrEnum):
    UNKNOWN = "unknown"
    VALID = "valid"
    EXPIRING = "expiring"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class KeyExpiryReading:
    """The state of the expiry of a key on a day, with the days left when the key has a date (R6.2.2)."""

    status: KeyExpiryStatus
    days_left: int | None = None


UNKNOWN_EXPIRY = KeyExpiryReading(KeyExpiryStatus.UNKNOWN)


@dataclass(frozen=True, slots=True)
class KeyExpiry:
    """The day the credentials of an adapter of a source stop working, in UTC, and who gave it (R6.2.2, ADR
    scadenza-delle-chiavi-letta-o-indicata).
    """

    expires_on: date
    source: KeyExpirySource

    @classmethod
    def read(cls, expires_on: date) -> KeyExpiry:
        return cls(expires_on, KeyExpirySource.READ)

    @classmethod
    def entered(cls, expires_on: date) -> KeyExpiry:
        return cls(expires_on, KeyExpirySource.ENTERED)

    @property
    def was_entered(self) -> bool:
        return self.source is KeyExpirySource.ENTERED

    def reading_on(self, today: date) -> KeyExpiryReading:
        days_left = (self.expires_on - today).days
        if days_left <= 0:
            return KeyExpiryReading(KeyExpiryStatus.EXPIRED, days_left)
        if days_left <= EXPIRING_WITHIN_DAYS:
            return KeyExpiryReading(KeyExpiryStatus.EXPIRING, days_left)
        return KeyExpiryReading(KeyExpiryStatus.VALID, days_left)


def expiry_reading_of(expiry: KeyExpiry | None, today: date) -> KeyExpiryReading:
    """Without a date the expiry is unknown, and the key raises no warning (R6.2.2)."""
    return UNKNOWN_EXPIRY if expiry is None else expiry.reading_on(today)


def utc_day_of(instant: datetime) -> date:
    """The day of an instant in UTC, the calendar the dates of expiry are kept in."""
    return instant.astimezone(UTC).date()
