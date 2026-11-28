"""Fake of the interval of the periodic reconciliation the flows context reads of the accounts of a tenant (Bug 778)."""

from collections.abc import Iterable
from datetime import timedelta
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError

DEFAULT_INTERVAL = timedelta(minutes=5)


class FakeAccountReconciliationIntervalsAdapter:
    """The accounts of the tenant, each with the default interval unless the test sets another."""

    def __init__(self, accounts: Iterable[UUID]) -> None:
        self.accounts = set(accounts)
        self.intervals: dict[UUID, timedelta] = {}

    def reconciliation_interval(self, account_id: UUID) -> timedelta:
        if account_id not in self.accounts:
            raise FlowAccountNotFoundError
        return self.intervals.get(account_id, DEFAULT_INTERVAL)
