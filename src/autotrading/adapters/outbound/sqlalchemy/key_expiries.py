from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from uuid import UUID, uuid5

from sqlalchemy import Connection, Engine, RowMapping, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.flow_repository import NOT_ARCHIVED, flow_of, flows_in_force
from autotrading.adapters.outbound.sqlalchemy.tables import accounts, key_expiry_notices, provider_keys
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_key import FlowKey
from autotrading.domain.notifications.expiring_key import ExpiringKey, KeyExpiryNotice, KeyKind
from autotrading.domain.tenancy.tenant_id import TenantId

# The key of a provider has no id of its own: its tenant and provider are its identity. A fixed namespace gives it the
# same id at every reading, so its alert and its notices find it again.
PROVIDER_KEY_NAMESPACE = UUID("6f0b3c2e-5a43-4c39-9a7e-0c1f3a6e2d47")


class SqlAlchemyKeyExpiriesAdapter:
    """Bound to the tenant of the daily check or of the cycle: the expiries of the credentials of its accounts and of
    the keys of its providers, with the flows not archived that use each (R6.2.2, ADR
    controllo-giornaliero-delle-scadenze). It reads them for the notifications and for the flows, under row level
    security; an account removed has no credentials left to expire.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def expiring_keys(self) -> tuple[ExpiringKey, ...]:
        account_rows, provider_rows, flows = self._read()
        return tuple(
            ExpiringKey(kind, key_id, key.name, key.expires_on, _users_of(key, flows))
            for kind, key_id, key in _keys_of(account_rows, provider_rows)
        )

    def dated_keys(self) -> tuple[FlowKey, ...]:
        account_rows, provider_rows, _ = self._read()
        return tuple(key for _, _, key in _keys_of(account_rows, provider_rows))

    def _read(self) -> tuple[Sequence[RowMapping], Sequence[RowMapping], list[Flow]]:
        dated_accounts = (
            select(accounts.c.id, accounts.c.name, accounts.c.expires_on)
            .where(accounts.c.expires_on.is_not(None), accounts.c.removed_at.is_(None))
            .order_by(accounts.c.name)
        )
        dated_keys = (
            select(provider_keys.c.provider, provider_keys.c.expires_on)
            .where(provider_keys.c.expires_on.is_not(None))
            .order_by(provider_keys.c.provider)
        )
        with self._transaction() as connection:
            account_rows = connection.execute(dated_accounts).mappings().all()
            provider_rows = connection.execute(dated_keys).mappings().all()
            flow_rows = connection.execute(flows_in_force().where(NOT_ARCHIVED)).mappings().all()
        return (
            account_rows,
            provider_rows,
            sorted((flow_of(row) for row in flow_rows), key=lambda flow: flow.name.value),
        )

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


class SqlAlchemyKeyExpiryNoticeRepositoryAdapter:
    """Bound to the tenant: the thresholds told for each expiry of its keys, once each, also when two checks run
    together (the primary key holds the key, its date and the threshold).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def record(self, notice: KeyExpiryNotice) -> bool:
        statement = (
            insert(key_expiry_notices)
            .values(
                tenant_id=self._tenant_id.value,
                key_kind=notice.kind.value,
                key_id=notice.key_id,
                expires_on=notice.expires_on,
                threshold=notice.threshold,
            )
            .on_conflict_do_nothing()
            .returning(key_expiry_notices.c.key_id)
        )
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            return connection.execute(statement).scalar_one_or_none() is not None


def provider_key_id(provider: str) -> UUID:
    return uuid5(PROVIDER_KEY_NAMESPACE, provider)


def _keys_of(
    account_rows: Sequence[RowMapping], provider_rows: Sequence[RowMapping]
) -> list[tuple[KeyKind, UUID, FlowKey]]:
    return [
        *(
            (KeyKind.ACCOUNT, row["id"], FlowKey(row["name"], row["expires_on"], account_id=row["id"]))
            for row in account_rows
        ),
        *(
            (
                KeyKind.PROVIDER,
                provider_key_id(row["provider"]),
                FlowKey(row["provider"], row["expires_on"], provider=row["provider"]),
            )
            for row in provider_rows
        ),
    ]


def _users_of(key: FlowKey, flows: list[Flow]) -> tuple[str, ...]:
    return tuple(flow.name.value for flow in flows if key.used_by(flow))
