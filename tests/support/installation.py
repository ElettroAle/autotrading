"""The configuration an installation receives, with the database secret as a file, as on the machine."""

import base64
from pathlib import Path

from nacl.public import PrivateKey


def installation_configuration(secrets: Path, **overrides: str) -> dict[str, str]:
    password_file = secrets / "postgres_app_password"
    password_file.write_text("unit-only\n", encoding="utf-8")
    public_key_file = secrets / "credentials_public_key"
    public_key_file.write_text(base64.b64encode(bytes(PrivateKey.generate().public_key)).decode(), encoding="utf-8")
    configuration = {
        "APP_VERSION": "1.0.0",
        "APP_ENVIRONMENT": "dev",
        "DATABASE_HOST": "postgres",
        "DATABASE_NAME": "autotrading",
        "DATABASE_USER": "autotrading_app",
        "DATABASE_PASSWORD_FILE": str(password_file),
        "CREDENTIALS_PUBLIC_KEY_FILE": str(public_key_file),
    }
    configuration.update(overrides)
    return configuration
