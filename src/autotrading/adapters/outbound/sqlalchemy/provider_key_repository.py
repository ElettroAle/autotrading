from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, RowMapping, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import provider_keys
from autotrading.application.agent.errors import ProviderKeyAlreadyRegisteredError, ProviderKeyNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId

PRIMARY_KEY = "provider_keys_pkey"


class SqlAlchemyProviderKeyRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def list(self) -> list[RegisteredProviderKey]:
        query = select(provider_keys).order_by(provider_keys.c.provider)
        with self._transaction() as connection:
            return [_key_of(row) for row in connection.execute(query).mappings()]

    def has_key(self, provider: ProviderName) -> bool:
        """The flows context asks only whether the tenant can use the provider (R1.4.1)."""
        return self.get(provider) is not None

    def get(self, provider: ProviderName) -> RegisteredProviderKey | None:
        query = select(provider_keys).where(provider_keys.c.provider == provider.value)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return None if row is None else _key_of(row)

    def add(self, key: RegisteredProviderKey) -> None:
        self._require_own(key)
        try:
            with self._transaction() as connection:
                connection.execute(insert(provider_keys).values(_row_of(key)))
        except IntegrityError as error:
            if PRIMARY_KEY in str(error.orig):
                raise ProviderKeyAlreadyRegisteredError(key.provider) from error
            raise

    def replace(self, key: RegisteredProviderKey) -> None:
        self._require_own(key)
        statement = (
            update(provider_keys)
            .where(provider_keys.c.provider == key.provider.value)
            .values(key_version=key.sealed.key_version, ciphertext=key.sealed.ciphertext, updated_at=func.now())
        )
        with self._transaction() as connection:
            if connection.execute(statement).rowcount != 1:
                raise ProviderKeyNotFoundError(key.provider)

    def remove(self, provider: ProviderName) -> None:
        statement = delete(provider_keys).where(provider_keys.c.provider == provider.value)
        with self._transaction() as connection:
            if connection.execute(statement).rowcount != 1:
                raise ProviderKeyNotFoundError(provider)

    def _require_own(self, key: RegisteredProviderKey) -> None:
        if key.tenant_id != self._tenant_id:
            raise CrossTenantAccessError

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row_of(key: RegisteredProviderKey) -> dict[str, object]:
    return {
        "tenant_id": key.tenant_id.value,
        "provider": key.provider.value,
        "key_version": key.sealed.key_version,
        "ciphertext": key.sealed.ciphertext,
    }


def _key_of(row: RowMapping) -> RegisteredProviderKey:
    return RegisteredProviderKey(
        TenantId(row["tenant_id"]),
        ProviderName(row["provider"]),
        SealedProviderKey(row["key_version"], row["ciphertext"]),
    )
