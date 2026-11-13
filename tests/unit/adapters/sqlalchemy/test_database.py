from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter

PASSWORD = "s3cret"  # noqa: S105 - test value
DATABASE = SqlAlchemyDatabaseAdapter(
    host="postgres", port=5432, name="autotrading", user="autotrading_app", password=PASSWORD
)


def test_url_targets_postgresql_through_psycopg() -> None:
    url = DATABASE.url()

    assert url.drivername == "postgresql+psycopg"
    assert (url.host, url.port, url.database, url.username, url.password) == (
        "postgres",
        5432,
        "autotrading",
        "autotrading_app",
        PASSWORD,
    )


def test_the_database_never_shows_the_password() -> None:
    assert PASSWORD not in repr(DATABASE)


def test_engine_url_hides_the_password() -> None:
    engine = DATABASE.engine()

    assert PASSWORD not in str(engine.url)
    assert engine.url.password == PASSWORD
