from dataclasses import dataclass, field

from sqlalchemy import URL, Engine, create_engine

APPLICATION_ROLE = "autotrading_app"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
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


def create_database_engine(settings: DatabaseSettings) -> Engine:
    return create_engine(settings.url(), pool_pre_ping=True)
