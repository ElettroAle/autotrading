from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.configuration import DEFAULT_PORT, _SqlAlchemySettings
from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter

type SqlAlchemyEngine = Engine


def sqlalchemy_adapters(host: str, port: str | None, name: str, user: str, password: str) -> SqlAlchemyEngine:
    """The engine every SQLAlchemy adapter of the installation runs on; the port is PostgreSQL's unless declared."""
    settings = _SqlAlchemySettings(host, name, user, password, DEFAULT_PORT if port is None else int(port))
    return SqlAlchemyDatabaseAdapter(
        settings.host, settings.port, settings.name, settings.user, settings.password
    ).engine()
