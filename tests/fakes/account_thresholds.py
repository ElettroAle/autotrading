"""Fake of what the flows context reads of the accounts of a tenant to compare their balance: name and threshold."""

from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError

DEFAULT_THRESHOLD = Decimal(1)


class FakeAccountThresholdsAdapter:
    """The accounts of the tenant by name, each with the default threshold unless the test sets another."""

    def __init__(self, names: Mapping[UUID, str]) -> None:
        self.names = dict(names)
        self.thresholds: dict[UUID, Decimal] = {}

    def deviation_threshold(self, account_id: UUID) -> Decimal:
        self.account_name(account_id)
        return self.thresholds.get(account_id, DEFAULT_THRESHOLD)

    def account_name(self, account_id: UUID) -> str:
        if account_id not in self.names:
            raise FlowAccountNotFoundError
        return self.names[account_id]
