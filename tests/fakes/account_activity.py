"""Fake of what the exchange shows of the accounts of a tenant: a reading per account, an empty one for an account
with nothing on the exchange, or out of reach.

It also holds the executions, funding and movements of each account, read since a moment as the exchange does. It
answers both ports the worker realizes with its reading use cases, the activity and the executions of an account.

The API process decorates the reading of the activity with a short memory (ADR
cache-delle-letture-del-conto-come-decorator-in-memoria): its fake keeps the readings on a clock the test moves.
"""

from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import overload
from uuid import UUID

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import AccountActivityPort
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.ledger import BalanceMovement, Execution, ExecutionsWindow, FundingPayment
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import an_activity


class _Reading(Enum):
    """Without a moment the fake answers the activity, with one the executions: the two ports it realizes."""

    ACTIVITY = "activity"


class FakeAccountActivityAdapter:
    def __init__(self) -> None:
        self.activities: dict[UUID, AccountActivity] = {}
        self.executions: dict[UUID, list[Execution]] = {}
        self.funding: dict[UUID, list[FundingPayment]] = {}
        self.movements: dict[UUID, list[BalanceMovement]] = {}
        self.complete = True
        self.reachable = True
        self.read: list[UUID] = []
        # What the exchange shows of an account the test set no reading for.
        self.unread: Callable[[UUID], AccountActivity] = lambda _: an_activity()

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
        if account_id in self.activities:
            return self.activities[account_id]
        return self.unread(account_id)

    def since(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return ExecutionsWindow(
            tuple(e for e in self.executions.get(account_id, []) if since is None or e.executed_at >= since),
            tuple(p for p in self.funding.get(account_id, []) if since is None or p.paid_at >= since),
            self.complete or since is None,
            tuple(m for m in self.movements.get(account_id, []) if since is None or m.moved_at >= since),
        )


class RememberedReadings:
    """The readings of the accounts of every tenant the API process keeps, each valid for the given seconds from the
    instant it arrived, on a clock in seconds the test moves; with no validity every reading is asked again.
    """

    def __init__(self, validity_seconds: float = 0.0) -> None:
        self.validity_seconds = validity_seconds
        self.seconds = 0.0
        self._readings: dict[tuple[TenantId, UUID], tuple[float, AccountActivity]] = {}

    def decorate(self, activity: AccountActivityPort, tenant_id: TenantId) -> FakeRememberedAccountActivityAdapter:
        """What the composition of the API does for each request: the reading of the account kept for its tenant."""
        return FakeRememberedAccountActivityAdapter(activity, tenant_id, self)

    def valid(self, tenant_id: TenantId, account_id: UUID) -> AccountActivity | None:
        arrived_at, activity = self._readings.get((tenant_id, account_id), (None, None))
        if arrived_at is None or self.seconds - arrived_at >= self.validity_seconds:
            return None
        return activity

    def keep(self, tenant_id: TenantId, account_id: UUID, activity: AccountActivity) -> None:
        self._readings[(tenant_id, account_id)] = (self.seconds, activity)


class FakeRememberedAccountActivityAdapter:
    """The decorator the composition of the API mounts on the reading of an account, bound to the tenant of the
    request: a reading still valid answers from the memory, any other asks the decorated port and is kept; an error is
    never kept and passes unchanged.
    """

    def __init__(self, decorated: AccountActivityPort, tenant_id: TenantId, readings: RememberedReadings) -> None:
        self._decorated = decorated
        self._tenant_id = tenant_id
        self._readings = readings

    def execute(self, account_id: UUID) -> AccountActivity:
        kept = self._readings.valid(self._tenant_id, account_id)
        if kept is not None:
            return kept
        activity = self._decorated.execute(account_id)
        self._readings.keep(self._tenant_id, account_id, activity)
        return activity
