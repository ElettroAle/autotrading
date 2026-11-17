"""The configuration an installation gives each service, with the secrets as files, as on the machine."""

import base64
from collections.abc import Callable
from pathlib import Path
from secrets import token_hex

from nacl.public import PrivateKey
from sqlalchemy import create_engine

from autotrading.adapters.outbound.hyperliquid.composition import (
    HyperliquidAdaptersOfInstallation,
    hyperliquid_adapters,
)
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.bootstrap import WorkerCycle, cycle_of
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.mail_service import FakeMailServiceAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter

# Generated per run, as prepare-installation.sh generates it per machine.
WORKER_TOKEN = token_hex(16)


def _secret(secrets: Path, name: str, content: str) -> str:
    location = secrets / name
    location.write_text(content, encoding="utf-8")
    return str(location)


def _database(secrets: Path) -> dict[str, str]:
    return {
        "APP_ENVIRONMENT": "dev",
        "DATABASE_HOST": "postgres",
        "DATABASE_NAME": "autotrading",
        "DATABASE_USER": "autotrading_app",
        "DATABASE_PASSWORD_FILE": _secret(secrets, "postgres_app_password", "unit-only\n"),
        "WORKER_TOKEN_FILE": _secret(secrets, "worker_token", f"{WORKER_TOKEN}\n"),
    }


def installation_configuration(secrets: Path, **overrides: str) -> dict[str, str]:
    """What the API receives: the public key of the credentials and the address of the worker."""
    public_key = base64.b64encode(bytes(PrivateKey.generate().public_key)).decode()
    configuration = _database(secrets) | {
        "APP_VERSION": "1.0.0",
        "CREDENTIALS_PUBLIC_KEY_FILE": _secret(secrets, "credentials_public_key", public_key),
        "WORKER_URL": "http://worker:8000",
    }
    return configuration | overrides


def worker_configuration(secrets: Path, **overrides: str) -> dict[str, str]:
    """What the worker receives: the private key of the credentials, which the API never does."""
    key = base64.b64encode(bytes(PrivateKey.generate())).decode()
    configuration = _database(secrets) | {
        "CREDENTIALS_PRIVATE_KEY_FILE": _secret(secrets, "credentials_private_key_v1", key),
        "FORECASTER_URL": "http://forecaster:8000",
    }
    return configuration | overrides


def dev_installation_on_testnet() -> tuple[str, HyperliquidAdaptersOfInstallation]:
    """The dev installation with Hyperliquid and Hyperliquid Testnet, as bootstrap hands them to the use cases
    (R2.3.11)."""
    return "dev", hyperliquid_adapters()


def cycles_of_installation(opener: SodiumCredentialOpenerAdapter) -> Callable[[TenantId], WorkerCycle]:
    """The cycles of the worker of an installation dev on the testnet, on a database that is never reached."""
    environment, hyperliquid = dev_installation_on_testnet()
    return cycle_of(
        create_engine("sqlite://"),
        (opener, SodiumProviderKeyOpenerAdapter({})),
        (environment, Slippage.default(), hyperliquid),
        (InMemoryOutboxAdapter(), FakeMailServiceAdapter()),
        ({}, FakePriceForecasterAdapter()),
    )
