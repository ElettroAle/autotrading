from sqlalchemy import Engine

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.sqlalchemy.configuration import _settings_of
from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter


def sqlalchemy_adapters(source: ConfigurationSource) -> Engine:
    """The engine of the database of the installation, on which every repository of the service is built."""
    settings = _settings_of(source)
    database = SqlAlchemyDatabaseAdapter(settings.host, settings.port, settings.name, settings.user, settings.password)
    return database.engine()
