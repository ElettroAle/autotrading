from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.account_references import reference_of
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import (
    ExecutionsReaderPort,
    ReferenceOpenerPort,
    SealedAddressPort,
)
from autotrading.domain.flows.ledger import ExecutionsWindow


class ReadAccountExecutionsUseCase:
    """In the worker: the executions the exchange still holds of an account, for its ledger (ADR 0063).

    The account is looked up for the tenant, then opened only for the fields its reader asks.
    """

    def __init__(
        self, accounts: SealedAddressPort, opener: ReferenceOpenerPort, readers: Mapping[str, ExecutionsReaderPort]
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def execute(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        sealed = self._accounts.sealed_address(account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.since(reference_of(self._opener, sealed, reader.reference_fields()), since)
