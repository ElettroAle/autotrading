from autotrading.adapters.outbound.sqlalchemy.database import DatabaseSettings, create_database_engine

PASSWORD = "s3cret"  # noqa: S105 - test value
SETTINGS = DatabaseSettings(host="postgres", port=5432, name="autotrading", user="autotrading_app", password=PASSWORD)


def test_url_targets_postgresql_through_psycopg() -> None:
    url = SETTINGS.url()

    assert url.drivername == "postgresql+psycopg"
    assert (url.host, url.port, url.database, url.username, url.password) == (
        "postgres",
        5432,
        "autotrading",
        "autotrading_app",
        PASSWORD,
    )


def test_settings_never_show_the_password() -> None:
    assert PASSWORD not in repr(SETTINGS)


def test_engine_url_hides_the_password() -> None:
    engine = create_database_engine(SETTINGS)

    assert PASSWORD not in str(engine.url)
    assert engine.url.password == PASSWORD
