import base64
import binascii
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import FastAPI
from sqlalchemy import Engine

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, AuthenticationSettings, OidcSigningKeys
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import WorkerUseCases, create_worker_api
from autotrading.adapters.outbound.httpx.account_state import TIMEOUT_SECONDS as WORKER_TIMEOUT_SECONDS
from autotrading.adapters.outbound.httpx.account_state import HttpxAccountStateAdapter
from autotrading.adapters.outbound.httpx.position_closing import HttpxPositionClosingAdapter
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.adapters.outbound.libsodium.opener import (
    InvalidPrivateCredentialsKeyError,
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError, SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.database import DatabaseSettings, create_database_engine
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, CredentialOpenerPort, ExchangePort
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.orders.ports import ExchangePort as OrderExchangePort
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

SUPPORTED_ENVIRONMENTS = ("dev", "prod")
DEFAULT_DATABASE_PORT = "5432"
DEFAULT_CREDENTIALS_KEY_VERSION = "1"
HYPERLIQUID = "Hyperliquid"
SLIPPAGE_SETTING = "ORDER_MAX_SLIPPAGE_PERCENT"


class MissingConfigurationError(AutotradingError):
    def __init__(self, name: str) -> None:
        super().__init__(f"configurazione mancante: {name}")
        self.name = name


class InvalidConfigurationError(AutotradingError):
    def __init__(self, name: str) -> None:
        super().__init__(f"configurazione non valida: {name}")
        self.name = name


class UndeclaredEnvironmentError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("ambiente non dichiarato")


class UnsupportedEnvironmentError(AutotradingError):
    def __init__(self, environment: str) -> None:
        super().__init__("ambiente non ammesso: sono ammessi " + " e ".join(SUPPORTED_ENVIRONMENTS))
        self.environment = environment


@dataclass(frozen=True, slots=True)
class PublicCredentialsKey:
    key: bytes = field(repr=False)
    version: int


@dataclass(frozen=True, slots=True)
class WorkerConnection:
    """How the API reaches the worker: its internal address and the token generated on the machine (ADR 0021)."""

    client: httpx.Client
    token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class WorkerExchanges:
    """The exchanges the worker reads accounts from and sends orders to, on the network of the installation."""

    accounts: Mapping[str, ExchangePort]
    orders: Mapping[str, OrderExchangePort]


class TradingAccessFromAccounts:
    """Bridges the accounts context to the orders context in the worker (ADR 0023).

    The account is looked up for the tenant under row level security, then opened with the private key only the
    worker holds; an account the tenant does not have is not found before anything is opened (R0.1.3).
    """

    def __init__(self, accounts: AccountRepositoryPort, opener: CredentialOpenerPort) -> None:
        self._accounts = accounts
        self._opener = opener

    def access(self, account_id: UUID) -> TradingAccess:
        try:
            account = find_account(self._accounts, AccountId(account_id))
        except AccountNotFoundError as error:
            raise OrderAccountNotFoundError from error
        credentials = self._opener.open(account)
        return TradingAccess(account.exchange.value, credentials.account_address, credentials.secret_key)


class TenantUseCaseFactory:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""

    def __init__(
        self,
        engine: Engine,
        public_key: PublicCredentialsKey,
        exchanges: Mapping[str, ExchangePort],
        worker: WorkerConnection,
    ) -> None:
        self._engine = engine
        self._public_key = public_key
        self._exchanges = exchanges
        self._worker = worker

    def for_tenant(self, tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        sealer = SodiumCredentialSealerAdapter(self._public_key.key, self._public_key.version, tenant_id)
        ports = TenantPorts(
            accounts=accounts,
            sealer=sealer,
            exchanges=self._exchanges,
            account_state=HttpxAccountStateAdapter(self._worker.client, self._worker.token, tenant_id),
            position_closing=HttpxPositionClosingAdapter(self._worker.client, self._worker.token, tenant_id),
        )
        return TenantUseCases.on(tenant_id, ports)


class WorkerUseCaseFactory:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names."""

    def __init__(
        self, engine: Engine, opener: SodiumCredentialOpenerAdapter, exchanges: WorkerExchanges, slippage: Slippage
    ) -> None:
        self._engine = engine
        self._opener = opener
        self._exchanges = exchanges
        self._slippage = slippage

    def for_tenant(self, tenant_id: TenantId) -> WorkerUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(self._engine, tenant_id)
        access = TradingAccessFromAccounts(accounts, self._opener)
        return WorkerUseCases(
            read_exchange_state=ReadExchangeStateUseCase(accounts, self._opener, self._exchanges.accounts),
            close_exchange_position=CloseExchangePositionUseCase(
                access, self._exchanges.orders, orders, self._slippage
            ),
        )


def create_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    health = HealthReport(
        version=_required(configuration, "APP_VERSION"),
        environment=_environment(configuration),
    )
    engine = _database(configuration)
    resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(engine))
    tenants = TenantUseCaseFactory(
        engine,
        PublicCredentialsKey(_credentials_public_key(configuration), _credentials_key_version(configuration)),
        exchanges_for(health.environment),
        _worker_connection(configuration),
    )
    return create_api(health, resolve_tenant, tenants.for_tenant, _authentication(configuration))


def create_worker_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    environment = _environment(configuration)
    opener = SodiumCredentialOpenerAdapter(
        {_credentials_key_version(configuration): _credentials_private_key(configuration)}
    )
    exchanges = WorkerExchanges(exchanges_for(environment), order_exchanges_for(environment))
    worker = WorkerUseCaseFactory(_database(configuration), opener, exchanges, slippage_from(configuration))
    return create_worker_api(_secret(configuration, "WORKER_TOKEN_FILE"), worker.for_tenant)


def exchanges_for(environment: str) -> dict[str, HyperliquidExchangeAdapter]:
    # The exchange network follows the installation: test networks in dev, real ones in prod (R0.2.1).
    return {HYPERLIQUID: HyperliquidExchangeAdapter.for_network(testnet=environment == "dev")}


def order_exchanges_for(environment: str) -> dict[str, HyperliquidOrderExchangeAdapter]:
    return {HYPERLIQUID: HyperliquidOrderExchangeAdapter.for_network(testnet=environment == "dev")}


def slippage_from(configuration: Mapping[str, str]) -> Slippage:
    """The largest distance from the current price an order accepts: 5% unless the installation says otherwise."""
    text = configuration.get(SLIPPAGE_SETTING, "").strip()
    if not text:
        return Slippage.default()
    try:
        percent = Decimal(text)
    except InvalidOperation as error:
        raise InvalidConfigurationError(SLIPPAGE_SETTING) from error
    if not percent.is_finite():
        raise InvalidConfigurationError(SLIPPAGE_SETTING)
    return Slippage.percent(percent)


def _credentials_public_key(configuration: Mapping[str, str]) -> bytes:
    name = "CREDENTIALS_PUBLIC_KEY_FILE"
    try:
        public_key = base64.b64decode(_secret(configuration, name), validate=True)
    except binascii.Error as error:
        raise InvalidCredentialsKeyError from error
    SodiumCredentialSealerAdapter(public_key, 0, TenantId.new())  # refuses a malformed key at startup
    return public_key


def _credentials_private_key(configuration: Mapping[str, str]) -> bytes:
    try:
        return base64.b64decode(_secret(configuration, "CREDENTIALS_PRIVATE_KEY_FILE"), validate=True)
    except binascii.Error as error:
        raise InvalidPrivateCredentialsKeyError from error


def _worker_connection(configuration: Mapping[str, str]) -> WorkerConnection:
    client = httpx.Client(base_url=_required(configuration, "WORKER_URL"), timeout=WORKER_TIMEOUT_SECONDS)
    return WorkerConnection(client, _secret(configuration, "WORKER_TOKEN_FILE"))


def _credentials_key_version(configuration: Mapping[str, str]) -> int:
    return int(configuration.get("CREDENTIALS_KEY_VERSION", DEFAULT_CREDENTIALS_KEY_VERSION))


def _database(configuration: Mapping[str, str]) -> Engine:
    settings = DatabaseSettings(
        host=_required(configuration, "DATABASE_HOST"),
        port=int(configuration.get("DATABASE_PORT", DEFAULT_DATABASE_PORT)),
        name=_required(configuration, "DATABASE_NAME"),
        user=_required(configuration, "DATABASE_USER"),
        # A secret is a mounted read-only file, never an environment variable (ADR 0015).
        password=_secret(configuration, "DATABASE_PASSWORD_FILE"),
    )
    return create_database_engine(settings)


def _authentication(configuration: Mapping[str, str]) -> Authentication | None:
    # Until the installation declares its identity provider, every protected function answers 503 (ADR 0016).
    if not configuration.get("AUTH_ISSUER", "").strip():
        return None
    settings = AuthenticationSettings(
        issuer=_required(configuration, "AUTH_ISSUER"),
        audience=_required(configuration, "AUTH_AUDIENCE"),
        client_id=_required(configuration, "AUTH_CLIENT_ID"),
        scope=_required(configuration, "AUTH_SCOPE"),
    )
    return Authentication(settings, AccessTokenVerifier(settings, OidcSigningKeys(settings.discovery_url)))


def _required(configuration: Mapping[str, str], name: str) -> str:
    value = configuration.get(name, "").strip()
    if not value:
        raise MissingConfigurationError(name)
    return value


def _secret(configuration: Mapping[str, str], name: str) -> str:
    secret = Path(_required(configuration, name)).read_text(encoding="utf-8").strip()
    if not secret:
        raise MissingConfigurationError(name)
    return secret


def _environment(configuration: Mapping[str, str]) -> str:
    environment = configuration.get("APP_ENVIRONMENT", "").strip()
    if not environment:
        raise UndeclaredEnvironmentError
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise UnsupportedEnvironmentError(environment)
    return environment
