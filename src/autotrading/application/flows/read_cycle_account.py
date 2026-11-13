from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.errors import (
    FlowCredentialsNotOpenedError,
    FlowCredentialsRefusedError,
    FlowCredentialsRejectedError,
    FlowExchangeUnavailableError,
)
from autotrading.application.flows.ports import (
    CycleAccessOpenerPort,
    CycleAccountReaderPort,
    FlowAccountNamePort,
    SealedAddressPort,
)
from autotrading.domain.flows.cycle_account import CycleAccount


@dataclass(frozen=True, slots=True)
class CycleAccountReading:
    """The account of the flow as a cycle reads it: its name and exchange, and what the exchange shows of it."""

    name: str
    exchange: str
    account: CycleAccount


class ReadCycleAccountUseCase:
    """In the worker: the account of a flow read on its exchange at every cycle, proving its credentials.

    Credentials that cannot be opened or that the exchange refuses are a permanent error of the account: every flow
    of the account pauses (R1.2.4).
    """

    def __init__(
        self,
        accounts: SealedAddressPort,
        names: FlowAccountNamePort,
        opener: CycleAccessOpenerPort,
        readers: Mapping[str, CycleAccountReaderPort],
    ) -> None:
        self._accounts = accounts
        self._names = names
        self._opener = opener
        self._readers = readers

    def execute(self, account_id: UUID) -> CycleAccountReading:
        sealed = self._accounts.sealed_address(account_id)
        name = self._names.account_name(account_id)
        reader = self._readers.get(sealed.exchange)
        if reader is None:
            raise FlowExchangeUnavailableError
        try:
            account = reader.cycle_reading(self._opener.open_cycle_access(sealed))
        except (FlowCredentialsNotOpenedError, FlowCredentialsRefusedError) as error:
            raise FlowCredentialsRejectedError(name, account_id) from error
        return CycleAccountReading(name, sealed.exchange, account)
