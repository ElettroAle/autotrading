"""The configuration an installation receives, with the database secret as a file, as on the machine."""

from pathlib import Path


def installation_configuration(secrets: Path, **overrides: str) -> dict[str, str]:
    password_file = secrets / "postgres_app_password"
    password_file.write_text("unit-only\n", encoding="utf-8")
    configuration = {
        "APP_VERSION": "1.0.0",
        "APP_ENVIRONMENT": "dev",
        "DATABASE_HOST": "postgres",
        "DATABASE_NAME": "autotrading",
        "DATABASE_USER": "autotrading_app",
        "DATABASE_PASSWORD_FILE": str(password_file),
    }
    configuration.update(overrides)
    return configuration
