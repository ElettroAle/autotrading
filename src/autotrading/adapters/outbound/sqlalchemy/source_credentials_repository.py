from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Connection, Engine, RowMapping, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import source_credentials
from autotrading.application.sources.errors import SourceCredentialsNotFoundError
from autotrading.application.sources.ports import SourceCredentialsRegistration
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.sources.key_expiry import KeyExpiry, KeyExpirySource
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemySourceCredentialsRepositoryAdapter:
    """Bound to the tenant of the request: the credentials it gave the adapters of the sources, under row level security
    (R4.1.2, ADR credenziali-degli-adapter-delle-fonti). It also tells the flows which adapters the tenant configured.

    The last configuration of an adapter is the instant the database stamped on its row.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def registrations(self) -> tuple[SourceCredentialsRegistration, ...]:
        query = select(source_credentials).order_by(source_credentials.c.adapter)
        with self._transaction() as connection:
            rows = connection.execute(query).mappings().all()
        return tuple(SourceCredentialsRegistration(_credentials_of(row), row["updated_at"]) for row in rows)

    def configured_adapters(self) -> frozenset[str]:
        with self._transaction() as connection:
            return frozenset(connection.execute(select(source_credentials.c.adapter)).scalars())

    def get(self, adapter: str) -> SourceCredentials | None:
        query = select(source_credentials).where(source_credentials.c.adapter == adapter)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return None if row is None else _credentials_of(row)

    def save(self, credentials: SourceCredentials) -> None:
        if credentials.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        row = _row_of(credentials)
        statement = insert(source_credentials).values(row)
        replacement = {name: statement.excluded[name] for name in row if name not in ("tenant_id", "adapter")}
        statement = statement.on_conflict_do_update(
            index_elements=[source_credentials.c.tenant_id, source_credentials.c.adapter],
            set_={**replacement, "updated_at": func.now()},
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def remove(self, adapter: str) -> None:
        statement = delete(source_credentials).where(source_credentials.c.adapter == adapter)
        with self._transaction() as connection:
            if connection.execute(statement).rowcount != 1:
                raise SourceCredentialsNotFoundError(adapter)

    def set_expiry(self, adapter: str, expiry: KeyExpiry | None) -> None:
        statement = (
            update(source_credentials)
            .where(source_credentials.c.adapter == adapter)
            .values(**_expiry_columns_of(expiry))
        )
        with self._transaction() as connection:
            if connection.execute(statement).rowcount != 1:
                raise SourceCredentialsNotFoundError(adapter)

    def mark_rejected(self, adapter: str, at: datetime) -> bool:
        # Only the first refusal since the last configuration counts: the user is told once.
        statement = (
            update(source_credentials)
            .where(source_credentials.c.adapter == adapter, source_credentials.c.rejected_at.is_(None))
            .values(rejected_at=at)
        )
        with self._transaction() as connection:
            return connection.execute(statement).rowcount == 1

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row_of(credentials: SourceCredentials) -> dict[str, object]:
    return {
        "tenant_id": credentials.tenant_id.value,
        "adapter": credentials.adapter,
        "public_values": dict(credentials.public_values),
        "key_version": credentials.sealed.key_version,
        "ciphertext": credentials.sealed.ciphertext,
        "rejected_at": credentials.rejected_at,
        **_expiry_columns_of(credentials.expiry),
    }


def _expiry_columns_of(expiry: KeyExpiry | None) -> dict[str, object]:
    if expiry is None:
        return {"expires_on": None, "expiry_source": None}
    return {"expires_on": expiry.expires_on, "expiry_source": expiry.source.value}


def _expiry_of(row: RowMapping) -> KeyExpiry | None:
    if row["expires_on"] is None:
        return None
    return KeyExpiry(row["expires_on"], KeyExpirySource(row["expiry_source"]))


def _public_values_of(stored: object) -> Mapping[str, str]:
    if not isinstance(stored, Mapping):
        return {}
    return {str(name): str(value) for name, value in stored.items()}


def _credentials_of(row: RowMapping) -> SourceCredentials:
    return SourceCredentials(
        TenantId(row["tenant_id"]),
        row["adapter"],
        _public_values_of(row["public_values"]),
        SealedSourceSecrets(row["key_version"], row["ciphertext"]),
        _expiry_of(row),
        row["rejected_at"],
    )
