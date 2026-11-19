"""Fake of the expiries of the keys of a tenant and of the thresholds told, as the database holds them (R6.2.2)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import time
from uuid import NAMESPACE_URL, UUID, uuid5

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_key import FlowKey
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.notifications.expiring_key import ExpiringKey, KeyExpiryNotice, KeyKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore
from tests.fakes.flow_repository import FlowStore
from tests.fakes.provider_keys import ProviderKeyStore
from tests.fakes.source_credentials import SourceCredentialsStore


def provider_key_id(provider: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"provider-key:{provider}")


def source_credentials_id(adapter: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"source-credentials:{adapter}")


class InMemoryKeyExpiriesAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security: the keys with an expiry and the flows
    not archived that use each; the credentials of the adapters of the sources are told, never paused for (R4.1.2)."""

    def __init__(
        self,
        accounts: AccountStore,
        keys: ProviderKeyStore,
        flows: FlowStore,
        tenant_id: TenantId,
        sources: SourceCredentialsStore | None = None,
    ) -> None:
        self._accounts = accounts
        self._keys = keys
        self._flows = flows
        self._tenant_id = tenant_id
        self._sources = SourceCredentialsStore() if sources is None else sources

    def expiring_keys(self) -> tuple[ExpiringKey, ...]:
        keys = tuple(
            ExpiringKey(kind, key_id, key.name, key.expires_on, self._users_of(key))
            for kind, key_id, key in self._keyed()
        )
        return (*keys, *self._source_keys())

    def _source_keys(self) -> tuple[ExpiringKey, ...]:
        flows = sorted(self._flows_in_use(), key=lambda flow: flow.name.value)
        return tuple(
            ExpiringKey(
                KeyKind.SOURCE,
                source_credentials_id(credentials.adapter),
                credentials.adapter,
                credentials.expiry.expires_on,
                tuple(
                    flow.name.value
                    for flow in flows
                    if any(active.adapter == credentials.adapter for active in flow.configuration.active_sources)
                ),
            )
            for credentials in self._sources.of(self._tenant_id)
            if credentials.expiry is not None
        )

    def dated_keys(self) -> tuple[FlowKey, ...]:
        return tuple(key for _, _, key in self._keyed())

    def _keyed(self) -> list[tuple[KeyKind, UUID, FlowKey]]:
        accounts = sorted(
            (account for account in self._accounts.of(self._tenant_id) if account.expiry is not None),
            key=lambda account: account.name.value,
        )
        keys = sorted(
            (key for key in self._keys.of(self._tenant_id) if key.expiry is not None),
            key=lambda key: key.provider.value,
        )
        return [
            *(
                (
                    KeyKind.ACCOUNT,
                    account.id.value,
                    FlowKey(account.name.value, account.expiry.expires_on, account_id=account.id.value),
                )
                for account in accounts
                if account.expiry is not None
            ),
            *(
                (
                    KeyKind.PROVIDER,
                    provider_key_id(key.provider.value),
                    FlowKey(key.provider.value, key.expiry.expires_on, provider=key.provider.value),
                )
                for key in keys
                if key.expiry is not None
            ),
        ]

    def _users_of(self, key: FlowKey) -> tuple[str, ...]:
        flows = sorted(self._flows_in_use(), key=lambda flow: flow.name.value)
        return tuple(flow.name.value for flow in flows if key.used_by(flow))

    def _flows_in_use(self) -> list[Flow]:
        return [
            flow
            for flow in self._flows.flows
            if flow.tenant_id == self._tenant_id and flow.status is not FlowStatus.ARCHIVED
        ]


@dataclass
class KeyExpiryNoticeStore:
    notices: dict[TenantId, set[KeyExpiryNotice]] = field(default_factory=dict)


class InMemoryKeyExpiryNoticeRepositoryAdapter:
    def __init__(self, store: KeyExpiryNoticeStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def record(self, notice: KeyExpiryNotice) -> bool:
        told = self._store.notices.setdefault(self._tenant_id, set())
        if notice in told:
            return False
        told.add(notice)
        return True


class FakeDailyCheckSchedulerAdapter:
    """Keeps the daily checks it is given; a test runs them as the scheduler would, at once and every day."""

    def __init__(self) -> None:
        self.checks: dict[str, tuple[time, Callable[[], None]]] = {}

    def keep_daily(self, name: str, at: time, run: Callable[[], None]) -> None:
        self.checks[name] = (at, run)

    def run_all(self) -> None:
        for _, run in self.checks.values():
            run()
