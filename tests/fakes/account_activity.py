"""Fake of what the exchange shows of the accounts of a tenant: a reading per account, an empty one for an account
with nothing on the exchange, or out of reach."""

from uuid import UUID

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity
from tests.support.activity import an_activity


class FakeAccountActivityAdapter:
    def __init__(self) -> None:
        self.activities: dict[UUID, AccountActivity] = {}
        self.reachable = True
        self.read: list[UUID] = []

    def activity(self, account_id: UUID) -> AccountActivity:
        self.read.append(account_id)
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities.get(account_id, an_activity())
