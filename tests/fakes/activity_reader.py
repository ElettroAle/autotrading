"""Fake of the adapter that reads what an exchange shows of an address: a reading per address, or out of reach.

It also holds the executions and funding of each address, read since a moment as the exchange does. A late execution
is published only after the first reading of its address, as the exchange may do with an execution of a moment ago.
And the deposits and withdrawals of each address, read in a window (R3.4.2).
"""

from datetime import datetime

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import AccountTransfer
from autotrading.domain.flows.ledger import Execution, ExecutionsWindow, FundingPayment
from autotrading.domain.flows.statistics_period import TimeWindow
from tests.support.activity import an_activity

# The field the fake exchange finds an account by, as the adapter of a real exchange declares its own.
ADDRESS_FIELD = "account_address"


class FakeActivityReaderAdapter:
    def __init__(self) -> None:
        self.activities: dict[str, AccountActivity] = {}
        self.executions: dict[str, list[Execution]] = {}
        self.late: dict[str, list[Execution]] = {}
        self.funding: dict[str, list[FundingPayment]] = {}
        self.complete = True
        self.reachable = True
        self.executions_reachable = True
        self.unreachable_after_first_reading = False
        self.readings: list[tuple[str, datetime | None]] = []
        self.declared: dict[str, list[AccountTransfer]] = {}
        self.transfer_readings: list[tuple[str, TimeWindow]] = []

    def reference_fields(self) -> frozenset[str]:
        return frozenset({ADDRESS_FIELD})

    def activity(self, reference: AccountReference) -> AccountActivity:
        address = reference.value(ADDRESS_FIELD)
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities.get(address, an_activity())

    def since(self, reference: AccountReference, since: datetime | None) -> ExecutionsWindow:
        address = reference.value(ADDRESS_FIELD)
        if not (self.reachable and self.executions_reachable):
            raise FlowExchangeUnavailableError
        self.readings.append((address, since))
        window = ExecutionsWindow(
            tuple(e for e in self.executions.get(address, []) if since is None or e.executed_at >= since),
            tuple(p for p in self.funding.get(address, []) if since is None or p.paid_at >= since),
            self.complete or since is None,
        )
        self.executions.setdefault(address, []).extend(self.late.pop(address, []))
        self.executions_reachable = not self.unreachable_after_first_reading
        return window

    def transfers(self, reference: AccountReference, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        address = reference.value(ADDRESS_FIELD)
        if not self.reachable:
            raise FlowExchangeUnavailableError
        self.transfer_readings.append((address, window))
        return tuple(each for each in self.declared.get(address, []) if window.contains(each.transferred_at))
