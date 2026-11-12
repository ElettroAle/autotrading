"""Fake of what the exchange shows of the accounts of a tenant: a reading per account, or out of reach.

It also holds the executions and funding of each account, read since a moment as the exchange does.
"""

from datetime import datetime
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.ledger import Execution, ExecutionsWindow, FundingPayment


class FakeAccountActivityAdapter:
    def __init__(self) -> None:
        self.activities: dict[UUID, AccountActivity] = {}
        self.executions: dict[UUID, list[Execution]] = {}
        self.funding: dict[UUID, list[FundingPayment]] = {}
        self.complete = True
        self.reachable = True

    def activity(self, account_id: UUID) -> AccountActivity:
        if account_id not in self.activities:
            raise FlowAccountNotFoundError
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities[account_id]

    def since(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return ExecutionsWindow(
            tuple(e for e in self.executions.get(account_id, []) if since is None or e.executed_at >= since),
            tuple(p for p in self.funding.get(account_id, []) if since is None or p.paid_at >= since),
            self.complete or since is None,
        )
