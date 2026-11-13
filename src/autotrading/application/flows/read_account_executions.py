from collections.abc import Mapping

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import (
    AddressOpenerPort,
    ExecutionsReaderPort,
    ReadAccountExecutionsCommand,
    SealedAddressPort,
)
from autotrading.domain.flows.ledger import ExecutionsWindow


class ReadAccountExecutionsUseCase:
    """In the worker: the executions the exchange still holds of an account, for its ledger (ADR 0063).

    The account is looked up for the tenant, then opened only to learn its address.
    """

    def __init__(
        self, accounts: SealedAddressPort, opener: AddressOpenerPort, readers: Mapping[str, ExecutionsReaderPort]
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def execute(self, command: ReadAccountExecutionsCommand) -> ExecutionsWindow:
        sealed = self._accounts.sealed_address(command.account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.since(self._opener.open_address(sealed), command.since)
