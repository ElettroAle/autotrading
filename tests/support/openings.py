"""The register of the openings of the credentials of the accounts and of the keys of the AI providers, as the threat
model reads it (Bug 179, docs/architecture.md §8.2): the fake openers write it as the opener of libsodium writes its
log, whose lines its own unit tests prove.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from autotrading.domain.tenancy.tenant_id import TenantId

# The instant of the openings of a fake opener no test reads the register of.
UNREAD_AT = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Opening:
    """Who was opened, for what, with which key, how it went and when; never what was opened."""

    purpose: str
    subject: str
    tenant_id: TenantId
    key_version: int
    opened: bool
    at: datetime


class OpeningRegister:
    def __init__(self, clock: Callable[[], datetime] = lambda: UNREAD_AT) -> None:
        self._clock = clock
        self.openings: list[Opening] = []

    def record(self, purpose: str, subject: str, tenant_id: TenantId, key_version: int, *, opened: bool) -> None:
        self.openings.append(Opening(purpose, subject, tenant_id, key_version, opened, self._clock()))

    def of(self, subject: str) -> list[Opening]:
        return [opening for opening in self.openings if opening.subject == subject]
