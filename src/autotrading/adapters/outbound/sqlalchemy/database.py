from dataclasses import dataclass, field

import sqlalchemy
from sqlalchemy import URL, Engine

APPLICATION_ROLE = "autotrading_app"


@dataclass(frozen=True, slots=True)
class SqlAlchemyDatabaseAdapter:
    """Where the database is and who connects: the engine it builds never shows the password."""

    host: str
    port: int
    name: str
    user: str
    password: str = field(repr=False)

    def url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        )

    def engine(self) -> Engine:
        # Read from the module at each call: the telemetry, installed first, wraps it to trace the queries (ADR
        # telemetria-opentelemetry-verso-grafana-cloud).
        return sqlalchemy.create_engine(self.url(), pool_pre_ping=True)
