"""Fake of what the exchange shows of the accounts of a tenant: a reading per account, an empty one for an account
with nothing on the exchange, or out of reach.

It also holds the executions and funding of each account, read since a moment as the exchange does. It answers both
ports the worker realizes with its reading use cases, the activity and the executions of an account.
"""

from datetime import datetime
from enum import Enum
from typing import overload
from uuid import UUID

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.ledger import Execution, ExecutionsWindow, FundingPayment
from tests.support.activity import an_activity


class _Reading(Enum):
    """Without a moment the fake answers the activity, with one the executions: the two ports it realizes."""

    ACTIVITY = "activity"


class FakeAccountActivityAdapter:
    def __init__(self) -> None:
        self.activities: dict[UUID, AccountActivity] = {}
        self.executions: dict[UUID, list[Execution]] = {}
        self.funding: dict[UUID, list[FundingPayment]] = {}
        self.complete = True
        self.reachable = True
        self.read: list[UUID] = []

    @overload
    def execute(self, account_id: UUID) -> AccountActivity: ...

    @overload
    def execute(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow: ...

    def execute(
        self, account_id: UUID, since: datetime | _Reading | None = _Reading.ACTIVITY
    ) -> AccountActivity | ExecutionsWindow:
        if since is _Reading.ACTIVITY:
            return self.activity(account_id)
        return self.since(account_id, since)

    def activity(self, account_id: UUID) -> AccountActivity:
        self.read.append(account_id)
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities.get(account_id, an_activity())

    def since(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return ExecutionsWindow(
            tuple(e for e in self.executions.get(account_id, []) if since is None or e.executed_at >= since),
            tuple(p for p in self.funding.get(account_id, []) if since is None or p.paid_at >= since),
            self.complete or since is None,
        )
