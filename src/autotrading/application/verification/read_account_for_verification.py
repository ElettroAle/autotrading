from collections.abc import Mapping

from autotrading.application.verification.errors import VerificationExchangeUnsupportedError
from autotrading.application.verification.ports import (
    AccountReaderPort,
    ReadAccountForVerificationCommand,
    VerificationAccountPort,
    VerificationOpenerPort,
)
from autotrading.domain.verification.reading import AccountReading


class ReadAccountForVerificationUseCase:
    """In the worker: what the exchange shows of the account the procedure runs on (ADR 0024).

    The account is looked up for the tenant, its exchange chosen, its credentials opened and proved on the exchange,
    as the worker reads it for the API; a failure is a failed step with its reason.
    """

    def __init__(
        self,
        accounts: VerificationAccountPort,
        opener: VerificationOpenerPort,
        readers: Mapping[str, AccountReaderPort],
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def execute(self, command: ReadAccountForVerificationCommand) -> AccountReading:
        sealed = self._accounts.sealed_verification(command.account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise VerificationExchangeUnsupportedError
        return reader.verification_reading(self._opener.open_verification(sealed))
