from dataclasses import dataclass
from datetime import UTC, date, time
from enum import StrEnum
from uuid import UUID

# The days before the expiry the user is told, and the day itself: once each (R6.2.2).
NOTICE_THRESHOLDS = (30, 7, 1, 0)
EXPIRING_WITHIN_DAYS = max(NOTICE_THRESHOLDS)
# Every day at this instant, and when the worker starts (ADR controllo-giornaliero-delle-scadenze).
DAILY_CHECK_AT = time(6, 0, tzinfo=UTC)


class KeyKind(StrEnum):
    """Which key: the credentials of an account, the key of a provider or the credentials of an adapter of a source
    (R6.2.2, R4.1.2)."""

    ACCOUNT = "account"
    PROVIDER = "provider"
    SOURCE = "source"


@dataclass(frozen=True, slots=True)
class KeyExpiryNotice:
    """A threshold already told for an expiry of a key: a new date is a new expiry, told again from the start."""

    kind: KeyKind
    key_id: UUID
    expires_on: date
    threshold: int


@dataclass(frozen=True, slots=True)
class ExpiringKey:
    """A key of the tenant with its expiry, by the name the user knows it by, and the flows that use it (R6.2.2).

    The day of the expiry is already expired: the key works until the day before.
    """

    kind: KeyKind
    key_id: UUID
    name: str
    expires_on: date
    flows: tuple[str, ...] = ()

    def days_left(self, today: date) -> int:
        return (self.expires_on - today).days

    def is_expired(self, today: date) -> bool:
        return self.days_left(today) <= 0

    def is_expiring(self, today: date) -> bool:
        """Within 30 days and not yet expired."""
        return 0 < self.days_left(today) <= EXPIRING_WITHIN_DAYS

    def notice_on(self, today: date) -> KeyExpiryNotice | None:
        """The nearest threshold reached on the day, none more than 30 days before the expiry."""
        days = self.days_left(today)
        reached = [threshold for threshold in NOTICE_THRESHOLDS if threshold >= days]
        if not reached:
            return None
        return KeyExpiryNotice(self.kind, self.key_id, self.expires_on, min(reached))

    def headline_on(self, today: date) -> str:
        """What happens to the key, by the days actually left: a key first seen within a threshold tells its own."""
        days = self.days_left(today)
        if days <= 0:
            return "è scaduta"
        if days == 1:
            return "scade domani"
        return f"scade tra {days} giorni"

    @property
    def subject(self) -> str:
        return f"chiave {self.name}"

    @property
    def expiry_text(self) -> str:
        return f"{self.expires_on:%d/%m/%Y}"

    @property
    def flows_text(self) -> str:
        return ", ".join(self.flows) or "nessuno"
