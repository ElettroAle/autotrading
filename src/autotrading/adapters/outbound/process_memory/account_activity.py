import threading
import time
from collections.abc import Callable
from uuid import UUID

from autotrading.application.flows.ports import AccountActivityPort
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.tenancy.tenant_id import TenantId

type _ReadingKey = tuple[TenantId, UUID]


class _AccountActivityStore:
    """The readings of the accounts of every tenant, one store for the whole process, lost when it stops.

    A reading is valid for the given seconds from the instant it arrived; the expired ones go when a reading is kept.
    """

    def __init__(self, validity_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._validity_seconds = validity_seconds
        self._clock = clock
        self._guard = threading.Lock()
        self._readings: dict[_ReadingKey, tuple[float, AccountActivity]] = {}

    def valid(self, tenant_id: TenantId, account_id: UUID) -> AccountActivity | None:
        with self._guard:
            reading = self._readings.get((tenant_id, account_id))
        if reading is None:
            return None
        arrived_at, activity = reading
        if not self._is_valid(arrived_at, self._clock()):
            return None
        return activity

    def keep(self, tenant_id: TenantId, account_id: UUID, activity: AccountActivity) -> None:
        arrived_at = self._clock()
        with self._guard:
            self._readings = {
                key: reading for key, reading in self._readings.items() if self._is_valid(reading[0], arrived_at)
            }
            self._readings[(tenant_id, account_id)] = (arrived_at, activity)

    def kept(self) -> set[_ReadingKey]:
        with self._guard:
            return set(self._readings)

    def _is_valid(self, arrived_at: float, now: float) -> bool:
        return now - arrived_at < self._validity_seconds


class ProcessMemoryAccountActivityAdapter(AccountActivityPort):
    """Decorates the reading of an account with a short memory in the process (Bug 635, ADR
    cache-delle-letture-del-conto-come-decorator-in-memoria): a reading still valid answers from the store, any other
    asks the decorated port and is kept. An error of the decorated port is never kept and passes unchanged.

    Bound to the tenant of the request: tenants and accounts never share a reading.
    """

    def __init__(self, decorated: AccountActivityPort, tenant_id: TenantId, store: _AccountActivityStore) -> None:
        self._decorated = decorated
        self._tenant_id = tenant_id
        self._store = store

    def __repr__(self) -> str:
        return f"ProcessMemoryAccountActivityAdapter(tenant_id={self._tenant_id.value})"

    def execute(self, account_id: UUID) -> AccountActivity:
        kept = self._store.valid(self._tenant_id, account_id)
        if kept is not None:
            return kept
        activity = self._decorated.execute(account_id)
        self._store.keep(self._tenant_id, account_id, activity)
        return activity
