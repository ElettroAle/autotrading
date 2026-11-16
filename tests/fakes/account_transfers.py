"""Fake of the deposits and withdrawals the exchange declares on the accounts, as the worker reads them for the API:
those of each account, an account the tenant does not have, or an exchange out of reach (R3.4.2)."""

from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.flows.capital_history import AccountTransfer
from autotrading.domain.flows.statistics_period import TimeWindow


class FakeAccountTransfersAdapter:
    def __init__(self) -> None:
        self.declared: dict[UUID, list[AccountTransfer]] = {}
        self.missing: set[UUID] = set()
        self.reachable = True
        self.windows: list[TimeWindow] = []

    def transfers(self, account_id: UUID, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        self.windows.append(window)
        if account_id in self.missing:
            raise FlowAccountNotFoundError
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return tuple(each for each in self.declared.get(account_id, []) if window.contains(each.transferred_at))
