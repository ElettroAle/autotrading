"""Fake of the limit of the exposure on one side the flows context reads of the accounts of a tenant (R5.5.5)."""

from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError


class FakeAccountExposureLimitsAdapter:
    """The accounts of the tenant, each without a limit unless the test sets one; it counts the readings."""

    def __init__(self, accounts: Iterable[UUID]) -> None:
        self.accounts = set(accounts)
        self.limits: dict[UUID, Decimal] = {}
        self.readings: list[UUID] = []

    def max_direction_exposure_percent(self, account_id: UUID) -> Decimal | None:
        if account_id not in self.accounts:
            raise FlowAccountNotFoundError
        self.readings.append(account_id)
        return self.limits.get(account_id)
