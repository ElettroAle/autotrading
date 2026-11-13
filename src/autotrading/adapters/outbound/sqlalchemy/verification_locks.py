from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Engine, Integer, cast, func, select

from autotrading.application.flows.errors import AssetUnderVerificationError

type LockKey = tuple[int, int]


class SqlAlchemyRunningVerificationsAdapter:
    """Keeps the assets of an account free of procedures of verification while the status of a flow changes (ADR 0079).

    Not bound to a tenant: the locks name an account, and an account belongs to one tenant only.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def kept_free(self, account_id: UUID, assets: Iterable[str]) -> Iterator[None]:
        with verification_locks(self._engine, account_id, assets) as busy:
            if busy is not None:
                raise AssetUnderVerificationError(busy)
            yield


@contextmanager
def verification_locks(engine: Engine, account_id: UUID, assets: Iterable[str]) -> Iterator[str | None]:
    """Holds the PostgreSQL advisory locks of the assets of the account until the context ends, or none of them.

    Gives the first asset already locked, or None when all are held. The locks belong to the session of a
    connection kept for the whole context, outside any transaction: whoever holds one, the API changing the status
    of a flow or the worker running the procedure, the other sees it, and a process that dies releases it.
    Only tries, never waits: two holders never wait on each other.
    """
    with engine.connect() as connection:
        held: list[LockKey] = []
        busy: str | None = None
        for asset in sorted(set(assets)):
            key = verification_lock_key(account_id, asset)
            if not connection.execute(select(func.pg_try_advisory_lock(*_integers(key)))).scalar_one():
                busy = asset
                break
            held.append(key)
        connection.commit()
        try:
            yield busy
        finally:
            for key in held:
                connection.execute(select(func.pg_advisory_unlock(*_integers(key))))
            connection.commit()


def verification_lock_key(account_id: UUID, asset: str) -> LockKey:
    """The account and the asset as the two 32-bit numbers PostgreSQL locks on.

    The pair has its own key space, apart from the single 64-bit keys that hold the flows during a cycle.
    """
    digest = sha256(f"{account_id}:{asset}".encode()).digest()
    return int.from_bytes(digest[:4], "big", signed=True), int.from_bytes(digest[4:8], "big", signed=True)


def _integers(key: LockKey) -> tuple[object, object]:
    # Bound as integers, or the driver may send bigints and PostgreSQL find no two-key function for them.
    return cast(key[0], Integer), cast(key[1], Integer)
