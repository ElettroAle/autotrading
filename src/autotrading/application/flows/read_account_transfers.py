from collections.abc import Mapping
from uuid import UUID

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import ReferenceOpenerPort, SealedAddressPort, TransfersReaderPort
from autotrading.domain.flows.capital_history import AccountTransfer
from autotrading.domain.flows.statistics_period import TimeWindow


class ReadAccountTransfersUseCase:
    """In the worker: the deposits and withdrawals the exchange declares on an account, for its history of the capital
    (R3.4.2, ADR storico-delle-variazioni-di-capitale).

    The account is looked up for the tenant, then opened only for the fields its reader asks (ADR 0044).
    """

    def __init__(
        self, accounts: SealedAddressPort, opener: ReferenceOpenerPort, readers: Mapping[str, TransfersReaderPort]
    ) -> None:
        self._accounts = accounts
        self._opener = opener
        self._readers = readers

    def execute(self, account_id: UUID, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        sealed = self._accounts.sealed_address(account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise FlowExchangeUnavailableError
        return reader.transfers(self._opener.open_reference(sealed, reader.reference_fields()), window)
