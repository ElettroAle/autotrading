"""Fake of the adapter that reads what an exchange shows of an address: a reading per address, or out of reach."""

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity
from tests.support.activity import an_activity


class FakeActivityReaderAdapter:
    def __init__(self) -> None:
        self.activities: dict[str, AccountActivity] = {}
        self.reachable = True

    def activity(self, address: str) -> AccountActivity:
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.activities.get(address, an_activity())
