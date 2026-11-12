import base64
import binascii
import logging
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import FastAPI
from sqlalchemy import Engine

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, AuthenticationSettings, OidcSigningKeys
from autotrading.adapters.inbound.api.tenant_use_cases import TenantPorts, TenantUseCases
from autotrading.adapters.inbound.api.worker import BotPolling, WorkerUseCases, create_worker_api
from autotrading.adapters.outbound.httpx.account_state import TIMEOUT_SECONDS as WORKER_TIMEOUT_SECONDS
from autotrading.adapters.outbound.httpx.account_state import HttpxAccountStateAdapter
from autotrading.adapters.outbound.httpx.position_closing import HttpxPositionClosingAdapter
from autotrading.adapters.outbound.httpx.provider_key_verifier import HttpxProviderKeyVerifierAdapter
from autotrading.adapters.outbound.httpx.telegram import (
    HttpxTelegramInboxAdapter,
    HttpxTelegramMessengerAdapter,
    telegram_client,
)
from autotrading.adapters.outbound.httpx.verification import HttpxVerificationAdapter
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.adapters.outbound.json.model_catalog import load_model_catalog
from autotrading.adapters.outbound.libsodium.opener import (
    InvalidPrivateCredentialsKeyError,
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError, SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.database import DatabaseSettings, create_database_engine
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.link_code_repository import (
    SqlAlchemyLinkCodeLookupAdapter,
    SqlAlchemyLinkCodeRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import SqlAlchemyLinkedChatRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.provider_key_repository import SqlAlchemyProviderKeyRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.verification_run_repository import (
    SqlAlchemyVerificationRunRepositoryAdapter,
)
from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    ExchangeUnavailableError,
    WorkerUnavailableError,
)
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    AccountStatePort,
    CredentialOpenerPort,
    ExchangePort,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.application.agent.errors import ProviderKeyNotFoundError
from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowExchangeUnavailableError,
    InvalidFlowSettingError,
)
from autotrading.application.flows.ports import FlowAccount, FlowRepositoryPort, MarketsPort
from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.application.notifications.link_chat import LinkChatUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import LinkStores, MessengerPort
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.application.orders.ports import ExchangePort as OrderExchangePort
from autotrading.application.sources.collect_source import CollectedSource
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.run_exchange_verification import RunExchangeVerificationUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.agent.agent_context import SourceData
from autotrading.domain.agent.errors import (
    ModelNotAvailableError,
    ParameterNotSupportedError,
    ParameterOutOfRangeError,
    UnknownParameterError,
)
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.errors import ModelRequiredError
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, ModelSelection, SourceSelection
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.order import Order, OrderOrigin, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.sources.errors import (
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    UnknownSourceParameterError,
)
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Opening
from autotrading.domain.verification.reading import AccountReading, PositionReading

SUPPORTED_ENVIRONMENTS = ("dev", "prod")
DEFAULT_DATABASE_PORT = "5432"
DEFAULT_CREDENTIALS_KEY_VERSION = "1"
HYPERLIQUID = "Hyperliquid"
SLIPPAGE_SETTING = "ORDER_MAX_SLIPPAGE_PERCENT"
# The sources of the platform (R1.3.1): one added here becomes selectable in every flow.
SOURCE_CATALOG = SourceCatalog((INDICATORS, PIVOTS, FORECAST, SENTIMENT_ALTERNATIVE_ME, SENTIMENT_COINMARKETCAP, NEWS))
# The models of the platform (R1.4.2): one added to the configuration file becomes selectable in every flow.
MODEL_CATALOG = load_model_catalog()
PROVIDER_TIMEOUT_SECONDS = 10.0
TELEGRAM_BOT_SETTING = "TELEGRAM_BOT_TOKEN_FILE"

operations = logging.getLogger("autotrading.bootstrap")


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


MODEL_REFUSALS = (ModelNotAvailableError, ParameterOutOfRangeError, ParameterNotSupportedError, UnknownParameterError)
SOURCE_REFUSALS = (SourceNotAvailableError, SourceParameterOutOfRangeError, UnknownSourceParameterError)


class ProviderKeyUsageFromFlows:
    """Bridges the flows context to the agent context in the API (ADR 0031).

    A key is in use while a flow active or paused runs on a model of its provider; a stopped flow runs no cycle.
    """

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def flows_using(self, provider: ProviderName) -> list[str]:
        return [
            flow.name.value
            for flow in self._flows.list()
            if flow.status.not_stopped and flow.model_provider == provider.value
        ]


class FlowDirectoryFromFlows:
    """Bridges the flows context to the cycles context (ADR 0046): the flows of the tenant are those it can consult."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def exists(self, flow_id: UUID) -> bool:
        return any(flow.id.value == flow_id for flow in self._flows.list())


class FlowAccountsFromAccounts:
    """Bridges the accounts context to the flows context in the API (ADR 0031).

    The account is looked up for the tenant first, then its balance is read now by the worker (R0.2.2).
    """

    def __init__(self, accounts: AccountRepositoryPort, account_state: AccountStatePort) -> None:
        self._accounts = accounts
        self._account_state = account_state

    def account(self, account_id: UUID) -> FlowAccount:
        try:
            account = find_account(self._accounts, AccountId(account_id))
            balance = self._account_state.read_state(account.id).balance
        except AccountNotFoundError as error:
            raise FlowAccountNotFoundError from error
        except (ExchangeUnavailableError, WorkerUnavailableError) as error:
            raise FlowExchangeUnavailableError from error
        return FlowAccount(account.exchange.value, balance.amount, balance.currency)


class ModelSettingsFromAgent:
    """Bridges the agent context to the flows context in the API (ADR 0031).

    A model of the catalog is usable only with a registered key of its provider (R1.4.1), and only with the
    parameters it admits (R1.4.2); a refusal reaches the flow with the reason the agent context gives.
    """

    def __init__(self, catalog: ModelCatalog, keys: ProviderKeyRepositoryPort) -> None:
        self._catalog = catalog
        self._keys = keys

    def selection(self, model: str, requested: Mapping[str, object]) -> ModelSelection:
        if not model.strip():
            raise ModelRequiredError
        try:
            definition = self._catalog.find(model)
            parameters = definition.settings(requested)
        except MODEL_REFUSALS as error:
            raise InvalidFlowSettingError(str(error)) from error
        if self._keys.get(definition.provider) is None:
            raise InvalidFlowSettingError(str(ProviderKeyNotFoundError(definition.provider)))
        return ModelSelection(definition.name, parameters)


class SourceSettingsFromSources:
    """Bridges the sources context to the flows context (ADR 0031): a source of the catalog, its parameters checked."""

    def __init__(self, catalog: SourceCatalog) -> None:
        self._catalog = catalog

    def selection(self, source: str, weight: int | None, requested: Mapping[str, int]) -> SourceSelection:
        try:
            parameters = self._catalog.find(source).settings(requested)
        except SOURCE_REFUSALS as error:
            raise InvalidFlowSettingError(str(error)) from error
        return SourceSelection(source, DEFAULT_WEIGHT if weight is None else weight, parameters)


def agent_sources_of(collected: Sequence[CollectedSource]) -> tuple[SourceData, ...]:
    """Bridges the sources context to the agent context: each collected value with the weight of its source (R1.3.2)."""
    return tuple(
        SourceData(source.source, source.weight, sample.asset, sample.values)
        for source in collected
        for sample in source.samples
    )


@dataclass(frozen=True, slots=True)
class ApiExchanges:
    """The exchanges the API checks credentials and tradable assets on, on the network of the installation."""

    accounts: Mapping[str, ExchangePort]
    markets: Mapping[str, MarketsPort]


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


class AccountReadingFromAccounts:
    """Bridges the accounts context to the verification context in the worker (ADR 0024).

    The state is read as the worker reads it for the API; a failure becomes a failed step with its message.
    """

    def __init__(self, read_exchange_state: ReadExchangeStateUseCase) -> None:
        self._read_exchange_state = read_exchange_state

    def read(self, account_id: UUID) -> AccountReading:
        try:
            state = self._read_exchange_state.execute(ReadExchangeStateCommand(AccountId(account_id)))
        except AccountNotFoundError as error:
            raise VerificationAccountNotFoundError from error
        except AutotradingError as error:
            raise VerificationStepError(str(error)) from error
        return AccountReading(
            balance=state.balance.amount,
            available_margin=state.available_margin.amount,
            currency=state.balance.currency,
            positions=tuple(
                PositionReading(position.coin, position.side.value, position.size, position.leverage)
                for position in state.positions
            ),
        )


class OrderExecutionFromOrders:
    """Bridges the orders context to the verification context in the worker (ADR 0024).

    Both orders carry the origin "procedura di verifica" and the user who launched it; a failure becomes a failed
    step with its message, and an order the exchange did not execute is a failed step with the reason.
    """

    def __init__(self, opening: OpenPositionUseCase, closing: CloseExchangePositionUseCase) -> None:
        self._opening = opening
        self._closing = closing

    def open(self, account_id: UUID, opening: Opening, user_id: UserId) -> OrderResult:
        command = OpenPositionCommand(
            account_id=account_id,
            coin=opening.coin,
            direction=Direction(opening.side),
            leverage=opening.leverage,
            value=opening.value,
            source=_verification_source(user_id),
        )
        return _result_of(lambda: self._opening.execute(command))

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderResult:
        command = CloseExchangePositionCommand(account_id, coin, _verification_source(user_id))
        return _result_of(lambda: self._closing.execute(command))


def _verification_source(user_id: UserId) -> OrderSource:
    return OrderSource(OrderOrigin.VERIFICATION, user_id.value)


def _result_of(send: Callable[[], Order]) -> OrderResult:
    try:
        order = send()
    except OrderAccountNotFoundError as error:
        raise VerificationAccountNotFoundError from error
    except AutotradingError as error:
        raise VerificationStepError(str(error)) from error
    execution, rejection = order.execution, order.rejection
    if execution is None:
        message = order.status.value if rejection is None else rejection.exchange_message
        return OrderResult(succeeded=False, message=message)
    return OrderResult(succeeded=True, fee=execution.fee, realized_pnl=execution.realized_pnl)


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """What the installation declares to the worker beyond its secrets."""

    environment: str
    slippage: Slippage


class TenantUseCaseFactory:
    """Builds, for each request, the adapters bound to its tenant and the use cases on top of them."""

    def __init__(
        self,
        engine: Engine,
        public_key: PublicCredentialsKey,
        exchanges: ApiExchanges,
        worker: WorkerConnection,
        providers: httpx.Client,
    ) -> None:
        self._engine = engine
        self._public_key = public_key
        self._exchanges = exchanges
        self._worker = worker
        self._provider_key_verifier = HttpxProviderKeyVerifierAdapter(providers)

    def for_tenant(self, tenant_id: TenantId) -> TenantUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        sealer = SodiumCredentialSealerAdapter(self._public_key.key, self._public_key.version, tenant_id)
        account_state = HttpxAccountStateAdapter(self._worker.client, self._worker.token, tenant_id)
        provider_keys = SqlAlchemyProviderKeyRepositoryAdapter(self._engine, tenant_id)
        flows = SqlAlchemyFlowRepositoryAdapter(self._engine, tenant_id)
        ports = TenantPorts(
            accounts=accounts,
            sealer=sealer,
            exchanges=self._exchanges.accounts,
            account_state=account_state,
            position_closing=HttpxPositionClosingAdapter(self._worker.client, self._worker.token, tenant_id),
            verification=HttpxVerificationAdapter(self._worker.client, self._worker.token, tenant_id),
            source_catalog=SOURCE_CATALOG,
            provider_keys=provider_keys,
            provider_key_sealer=SodiumProviderKeySealerAdapter(
                self._public_key.key, self._public_key.version, tenant_id
            ),
            provider_key_verifier=self._provider_key_verifier,
            provider_key_usage=ProviderKeyUsageFromFlows(flows),
            model_catalog=MODEL_CATALOG,
            flows=flows,
            flow_checks=FlowChecks(
                accounts=FlowAccountsFromAccounts(accounts, account_state),
                markets=self._exchanges.markets,
                models=ModelSettingsFromAgent(MODEL_CATALOG, provider_keys),
                sources=SourceSettingsFromSources(SOURCE_CATALOG),
            ),
            link_codes=SqlAlchemyLinkCodeRepositoryAdapter(self._engine, tenant_id),
            linked_chats=SqlAlchemyLinkedChatRepositoryAdapter(self._engine, tenant_id),
            clock=now,
            closed_positions=SqlAlchemyClosedPositionRepositoryAdapter(self._engine, tenant_id),
            cycle_history=SqlAlchemyCycleRepositoryAdapter(self._engine, tenant_id),
            flow_directory=FlowDirectoryFromFlows(flows),
        )
        return TenantUseCases.on(tenant_id, ports)


class WorkerUseCaseFactory:
    """Builds, for each request of the API, the worker use cases on adapters bound to the tenant it names."""

    def __init__(
        self,
        engine: Engine,
        opener: SodiumCredentialOpenerAdapter,
        exchanges: WorkerExchanges,
        settings: WorkerSettings,
        messenger: MessengerPort,
    ) -> None:
        self._engine = engine
        self._opener = opener
        self._exchanges = exchanges
        self._settings = settings
        self._messenger = messenger

    def for_tenant(self, tenant_id: TenantId) -> WorkerUseCases:
        accounts = SqlAlchemyAccountRepositoryAdapter(self._engine, tenant_id)
        orders = SqlAlchemyOrderRepositoryAdapter(self._engine, tenant_id)
        access = TradingAccessFromAccounts(accounts, self._opener)
        slippage = self._settings.slippage
        read_exchange_state = ReadExchangeStateUseCase(accounts, self._opener, self._exchanges.accounts)
        close_exchange_position = CloseExchangePositionUseCase(access, self._exchanges.orders, orders, slippage)
        open_position = OpenPositionUseCase(access, self._exchanges.orders, orders, slippage)
        return WorkerUseCases(
            read_exchange_state=read_exchange_state,
            close_exchange_position=close_exchange_position,
            run_exchange_verification=RunExchangeVerificationUseCase(
                AccountReadingFromAccounts(read_exchange_state),
                OrderExecutionFromOrders(open_position, close_exchange_position),
                SqlAlchemyVerificationRunRepositoryAdapter(self._engine, tenant_id),
                self._settings.environment,
                now,
            ),
            notify=NotifyUseCase(SqlAlchemyLinkedChatRepositoryAdapter(self._engine, tenant_id), self._messenger),
        )

    def link_stores_for(self, tenant_id: TenantId) -> LinkStores:
        return LinkStores(
            SqlAlchemyLinkCodeRepositoryAdapter(self._engine, tenant_id),
            SqlAlchemyLinkedChatRepositoryAdapter(self._engine, tenant_id),
        )


class UnconfiguredMessenger:
    """Stands for Telegram until the installation has the token of the bot: every notification is a recorded
    failure, and the flows go on (ADR 0035).
    """

    def send(self, chat_id: ChatId, text: str) -> None:  # noqa: ARG002 - the signature of the port
        raise MessageNotDeliveredError


def now() -> datetime:
    return datetime.now(UTC)


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
        ApiExchanges(exchanges_for(health.environment), markets_for(health.environment)),
        _worker_connection(configuration),
        httpx.Client(timeout=PROVIDER_TIMEOUT_SECONDS),
    )
    return create_api(health, resolve_tenant, tenants.for_tenant, _authentication(configuration))


def create_worker_application(configuration: Mapping[str, str] = os.environ) -> FastAPI:
    """The worker: the only service that receives the private key of the credentials (ADR 0007, ADR 0021)."""
    environment = _environment(configuration)
    opener = SodiumCredentialOpenerAdapter(
        {_credentials_key_version(configuration): _credentials_private_key(configuration)}
    )
    exchanges = WorkerExchanges(exchanges_for(environment), order_exchanges_for(environment))
    settings = WorkerSettings(environment, slippage_from(configuration))
    engine = _database(configuration)
    token = _optional_secret(configuration, TELEGRAM_BOT_SETTING)
    client = None if token is None else telegram_client(token)
    messenger: MessengerPort = UnconfiguredMessenger() if client is None else HttpxTelegramMessengerAdapter(client)
    worker = WorkerUseCaseFactory(engine, opener, exchanges, settings, messenger)
    bot = None if client is None else telegram_bot(engine, worker, client, messenger)
    if bot is None:
        operations.warning("bot Telegram non configurato: notifiche disattivate")
    return create_worker_api(_secret(configuration, "WORKER_TOKEN_FILE"), worker.for_tenant, bot)


def telegram_bot(
    engine: Engine, worker: WorkerUseCaseFactory, client: httpx.Client, messenger: MessengerPort
) -> BotPolling:
    """The only bot of the platform, in long polling inside the worker: no inbound port (ADR 0035)."""
    link_chat = LinkChatUseCase(SqlAlchemyLinkCodeLookupAdapter(engine), worker.link_stores_for, messenger, now)
    return BotPolling(AnswerBotMessagesUseCase(HttpxTelegramInboxAdapter(client), link_chat).execute)


def exchanges_for(environment: str) -> dict[str, HyperliquidExchangeAdapter]:
    # The exchange network follows the installation: test networks in dev, real ones in prod (R0.2.1).
    return {HYPERLIQUID: HyperliquidExchangeAdapter.for_network(testnet=environment == "dev")}


def markets_for(environment: str) -> dict[str, HyperliquidMarketsAdapter]:
    return {HYPERLIQUID: HyperliquidMarketsAdapter.for_network(testnet=environment == "dev")}


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


def _optional_secret(configuration: Mapping[str, str], name: str) -> str | None:
    """A secret the installation may not have yet: unset, missing or empty means absent, never an error."""
    location = configuration.get(name, "").strip()
    if not location or not Path(location).is_file():
        return None
    return Path(location).read_text(encoding="utf-8").strip() or None


def _environment(configuration: Mapping[str, str]) -> str:
    environment = configuration.get("APP_ENVIRONMENT", "").strip()
    if not environment:
        raise UndeclaredEnvironmentError
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise UnsupportedEnvironmentError(environment)
    return environment
