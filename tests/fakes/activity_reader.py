"""Fake of the adapter that reads what an exchange shows of an address: a reading per address, or out of reach.

It also holds the executions and funding of each address, read since a moment as the exchange does.
"""

from datetime import datetime

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.ledger import Execution, ExecutionsWindow, FundingPayment
from tests.support.activity import an_activity


class FakeActivityReaderAdapter:
    def __init__(self) -> None:
        self.activities: dict[str, AccountActivity] = {}
        self.executions: dict[str, list[Execution]] = {}
        self.funding: dict[str, list[FundingPayment]] = {}
        self.complete = True
        self.reachable = True
        self.executions_reachable = True
        self.readings: list[tuple[str, datetime | None]] = []

    def activity(self, address: str) -> AccountActivity:
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities.get(address, an_activity())

    def since(self, address: str, since: datetime | None) -> ExecutionsWindow:
        if not (self.reachable and self.executions_reachable):
            raise FlowExchangeUnavailableError
        self.readings.append((address, since))
        return ExecutionsWindow(
            tuple(e for e in self.executions.get(address, []) if since is None or e.executed_at >= since),
            tuple(p for p in self.funding.get(address, []) if since is None or p.paid_at >= since),
            self.complete or since is None,
        )
