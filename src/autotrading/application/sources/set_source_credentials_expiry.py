from dataclasses import dataclass
from datetime import date

from autotrading.application.sources.ports import SourceCredentialsRepositoryPort
from autotrading.domain.sources.key_expiry import KeyExpiry


@dataclass(frozen=True, slots=True)
class SetSourceCredentialsExpiryCommand:
    adapter: str
    # None forgets the date: the expiry is unknown again.
    expires_on: date | None


class SetSourceCredentialsExpiryUseCase:
    """Keeps the day the user says the credentials of an adapter stop working, or forgets it: no adapter of a source
    reads it (R6.2.2, ADR credenziali-degli-adapter-delle-fonti).

    A new date is a new expiry: the notices of the old one do not count for it (R6.2.2).
    """

    def __init__(self, credentials: SourceCredentialsRepositoryPort) -> None:
        self._credentials = credentials

    def execute(self, command: SetSourceCredentialsExpiryCommand) -> None:
        expiry = None if command.expires_on is None else KeyExpiry.entered(command.expires_on)
        self._credentials.set_expiry(command.adapter, expiry)
