from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Connection, Engine, Integer, cast, func, select

# The first of the two 32-bit numbers of the lock: the reconciliations of the accounts, apart from every other lock.
ACCOUNT_RECONCILIATION_SPACE = 778


class SqlAlchemyAccountReconciliationLockAdapter:
    """Holds an account for one reconciliation with a PostgreSQL advisory lock (Bug 778, ADR
    riconciliazione-periodica-dei-conti-con-posizioni-aperte).

    The key is a pair of 32-bit numbers, a key space apart from the single 64-bit keys that hold the flows during a
    cycle: holding an account never holds its flows. The lock belongs to the session of a connection kept for the whole
    reconciliation, outside any transaction, and is released with the connection even if the worker dies. Not bound to
    a tenant: it names an account, and an account belongs to one tenant only.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def hold(self, account_id: UUID) -> Iterator[None]:
        with self._engine.connect() as connection:
            connection.execute(select(func.pg_advisory_lock(*account_reconciliation_key(account_id))))
            connection.commit()
            try:
                yield
            finally:
                _unlock(connection, account_id)

    @contextmanager
    def try_hold(self, account_id: UUID) -> Iterator[bool]:
        with self._engine.connect() as connection:
            key = account_reconciliation_key(account_id)
            acquired = bool(connection.execute(select(func.pg_try_advisory_lock(*key))).scalar_one())
            connection.commit()
            try:
                yield acquired
            finally:
                if acquired:
                    _unlock(connection, account_id)


def account_reconciliation_key(account_id: UUID) -> tuple[object, object]:
    """The account as the second number of the pair: its first four bytes, bound as integers, or the driver may send
    bigints and PostgreSQL find no two-key function for them. Two accounts that share them only wait on each other."""
    account = int.from_bytes(account_id.bytes[:4], "big", signed=True)
    return cast(ACCOUNT_RECONCILIATION_SPACE, Integer), cast(account, Integer)


def _unlock(connection: Connection, account_id: UUID) -> None:
    connection.execute(select(func.pg_advisory_unlock(*account_reconciliation_key(account_id))))
    connection.commit()
