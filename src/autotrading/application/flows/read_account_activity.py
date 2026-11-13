from collections.abc import Mapping
from uuid import UUID

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import (
    ActivityReaderPort,
    AddressOpenerPort,
    SealedAddressPort,
)
from autotrading.domain.flows.account_activity import AccountActivity


class ReadAccountActivityUseCase:
    """In the worker: what the exchange shows of an account, for the flows of the cycle and for the API (R1.6.1).

    The account is looked up for the tenant, then opened only to learn its address (ADR 0044).
    """

    def __init__(
        self, accounts: SealedAddressPort, opener: AddressOpenerPort, readers: Mapping[str, ActivityReaderPort]
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def execute(self, account_id: UUID) -> AccountActivity:
        sealed = self._accounts.sealed_address(account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.activity(self._opener.open_address(sealed))
