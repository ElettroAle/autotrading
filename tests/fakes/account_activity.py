"""Fake of what the exchange shows of the accounts of a tenant: a reading per account, or out of reach."""

from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity


class FakeAccountActivityAdapter:
    def __init__(self) -> None:
        self.activities: dict[UUID, AccountActivity] = {}
        self.reachable = True

    def activity(self, account_id: UUID) -> AccountActivity:
        if account_id not in self.activities:
            raise FlowAccountNotFoundError
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities[account_id]
