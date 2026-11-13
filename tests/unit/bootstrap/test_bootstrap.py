import base64
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from sqlalchemy import create_engine

from autotrading import bootstrap
from autotrading.adapters.outbound.httpx.provider_key_verifier import KEY_CHECKS
from autotrading.adapters.outbound.libsodium.opener import (
    InvalidPrivateCredentialsKeyError,
    SodiumCredentialOpenerAdapter,
)
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError
from autotrading.adapters.outbound.worker.composition import worker_adapters
from autotrading.application.accounts.errors import ExchangeUnavailableError
from autotrading.application.accounts.read_account_state import ReadAccountStateCommand
from autotrading.application.agent.errors import ProviderRejectedKeyError
from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    FlowOpeningsPort,
    FlowPositionsPort,
    FlowRepositoryPort,
    PositionClosedNoticePort,
    RunningCyclePort,
)
from autotrading.application.flows.record_manual_closing import RecordManualClosingUseCase
from autotrading.application.flows.stop_flow import StopPorts
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.orders.close_position import ClosePositionCommand
from autotrading.application.orders.errors import OrderAccountNotFoundError, OrderExchangeUnavailableError
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError
from autotrading.application.verification.run_verification import RunVerificationCommand
from autotrading.bootstrap import (
    MODEL_CATALOG,
    SLIPPAGE_SETTING,
    ApiExchanges,
    InvalidConfigurationError,
    MissingConfigurationError,
    PublicCredentialsKey,
    UndeclaredEnvironmentError,
    UnsupportedEnvironmentError,
    WorkerExchanges,
    WorkerSettings,
    activity_readers_for,
    create_application,
    create_worker_application,
    exchanges_for,
    executions_readers_for,
    markets_for,
    order_exchanges_for,
    slippage_from,
    tenant_use_cases,
    worker_use_cases,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.provider_keys import InMemoryProviderKeyRepositoryAdapter, ProviderKeyStore
from tests.support.accounts import an_account
from tests.support.installation import WORKER_TOKEN, installation_configuration, worker_configuration
from tests.support.problems import reason_of
from tests.support.worker import Worker

AUTHENTICATION = {
    "AUTH_ISSUER": "https://login.example.test/tenant/v2.0",
    "AUTH_AUDIENCE": "api://autotrading",
    "AUTH_CLIENT_ID": "swagger-client",
    "AUTH_SCOPE": "api://autotrading/access",
}


def test_application_exposes_configured_version_and_environment(tmp_path: Path) -> None:
    application = create_application(installation_configuration(tmp_path, APP_VERSION="1.2.1", APP_ENVIRONMENT="prod"))

    response = TestClient(application).get("/health")

    assert response.json() == {"version": "1.2.1", "environment": "prod"}


def test_application_refuses_to_start_without_version(tmp_path: Path) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, APP_VERSION="  "))

    assert raised.value.name == "APP_VERSION"
    assert str(raised.value) == "configurazione mancante: APP_VERSION"


@pytest.mark.parametrize("environment", [None, " "], ids=["absent", "blank"])
def test_application_refuses_to_start_without_environment(tmp_path: Path, environment: str | None) -> None:
    configuration = installation_configuration(tmp_path)
    if environment is None:
        del configuration["APP_ENVIRONMENT"]
    else:
        configuration["APP_ENVIRONMENT"] = environment

    with pytest.raises(UndeclaredEnvironmentError) as raised:
        create_application(configuration)

    assert str(raised.value) == "ambiente non dichiarato"


@pytest.mark.parametrize("environment", ["staging", "Dev", "production"])
def test_application_refuses_to_start_with_an_unsupported_environment(tmp_path: Path, environment: str) -> None:
    with pytest.raises(UnsupportedEnvironmentError) as raised:
        create_application(installation_configuration(tmp_path, APP_ENVIRONMENT=environment))

    assert raised.value.environment == environment
    assert str(raised.value) == "ambiente non ammesso: sono ammessi dev e prod"


def test_environment_is_accepted_with_surrounding_spaces(tmp_path: Path) -> None:
    application = create_application(installation_configuration(tmp_path, APP_ENVIRONMENT=" dev\n"))

    assert TestClient(application).get("/health").json()["environment"] == "dev"


@pytest.mark.parametrize("name", ["DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD_FILE"])
def test_application_refuses_to_start_without_the_database(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, **{name: ""}))

    assert raised.value.name == name


def test_application_refuses_to_start_with_an_empty_database_secret(tmp_path: Path) -> None:
    configuration = installation_configuration(tmp_path)
    Path(configuration["DATABASE_PASSWORD_FILE"]).write_text("\n", encoding="utf-8")

    with pytest.raises(MissingConfigurationError) as raised:
        create_application(configuration)

    assert raised.value.name == "DATABASE_PASSWORD_FILE"


def test_without_an_issuer_every_protected_function_is_refused_as_not_configured(tmp_path: Path) -> None:
    client = TestClient(create_application(installation_configuration(tmp_path)))

    response = client.get("/me", headers={"Authorization": "Bearer any-token"})

    assert (response.status_code, reason_of(response)) == (503, {"detail": "autenticazione non configurata"})


def test_with_an_issuer_the_openapi_page_logs_in_with_it(tmp_path: Path) -> None:
    client = TestClient(create_application(installation_configuration(tmp_path, **AUTHENTICATION)))

    page = client.get("/docs").text

    assert '"usePkceWithAuthorizationCodeGrant": true' in page
    assert '"clientId": "swagger-client"' in page


@pytest.mark.parametrize("name", ["AUTH_AUDIENCE", "AUTH_CLIENT_ID", "AUTH_SCOPE"])
def test_an_issuer_without_the_rest_of_the_login_refuses_to_start(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, **{**AUTHENTICATION, name: " "}))

    assert raised.value.name == name


def test_application_refuses_to_start_without_the_credentials_key(tmp_path: Path) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, CREDENTIALS_PUBLIC_KEY_FILE=""))

    assert raised.value.name == "CREDENTIALS_PUBLIC_KEY_FILE"


@pytest.mark.parametrize("content", ["not base64 at all!", "c2hvcnQ="], ids=["not-base64", "short-key"])
def test_application_refuses_to_start_with_a_malformed_credentials_key(tmp_path: Path, content: str) -> None:
    configuration = installation_configuration(tmp_path)
    Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).write_text(content, encoding="utf-8")

    with pytest.raises(InvalidCredentialsKeyError):
        create_application(configuration)


def test_each_tenant_gets_use_cases_bound_to_it(tmp_path: Path) -> None:
    configuration = installation_configuration(tmp_path)
    public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
    worker = worker_adapters("http://worker:8000", WORKER_TOKEN)
    factory = tenant_use_cases(
        create_engine("sqlite://"), PublicCredentialsKey(public_key, 1), ApiExchanges({}, {}), worker, httpx.Client()
    )

    first, second = factory(TenantId.new()), factory(TenantId.new())

    assert first.register_account is not second.register_account
    assert first.read_account_state is not second.read_account_state


def test_the_worker_is_asked_for_the_tenant_of_the_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store, tenant_id = AccountStore(), TenantId.new()
    account = an_account(tenant_id)
    store.accounts.append(account)
    monkeypatch.setattr(
        bootstrap,
        "SqlAlchemyAccountRepositoryAdapter",
        lambda _, tenant: InMemoryAccountRepositoryAdapter(store, tenant),
    )
    asked: list[httpx.Request] = []

    def worker_answer(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return httpx.Response(503, json={"detail": "exchange non raggiungibile"})

    configuration = installation_configuration(tmp_path)
    public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
    worker = worker_adapters("http://worker:8000", WORKER_TOKEN, httpx.MockTransport(worker_answer))
    factory = tenant_use_cases(
        create_engine("sqlite://"), PublicCredentialsKey(public_key, 1), ApiExchanges({}, {}), worker, httpx.Client()
    )

    with pytest.raises(ExchangeUnavailableError):
        factory(tenant_id).read_account_state.execute(ReadAccountStateCommand(account.id))

    assert [request.url.path for request in asked] == [f"/tenants/{tenant_id.value}/accounts/{account.id.value}/state"]
    assert asked[0].headers["Authorization"] == f"Bearer {WORKER_TOKEN}"


@pytest.mark.parametrize("name", ["WORKER_URL", "WORKER_TOKEN_FILE"])
def test_application_refuses_to_start_without_the_worker(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, **{name: ""}))

    assert raised.value.name == name


def test_the_worker_answers_only_with_the_token_generated_on_the_machine(tmp_path: Path) -> None:
    client = TestClient(create_worker_application(worker_configuration(tmp_path)))
    path = f"/tenants/{uuid4()}/accounts/{uuid4()}/state"

    response = client.get(path, headers={"Authorization": "Bearer another-token"})

    assert (response.status_code, reason_of(response)) == (401, {"detail": "non autenticato"})
    assert client.get("/health").json() == {"status": "ok"}


def test_the_worker_publishes_no_documentation(tmp_path: Path) -> None:
    client = TestClient(create_worker_application(worker_configuration(tmp_path)))

    assert (client.get("/openapi.json").status_code, client.get("/docs").status_code) == (404, 404)


@pytest.mark.parametrize(
    "name", ["APP_ENVIRONMENT", "CREDENTIALS_PRIVATE_KEY_FILE", "WORKER_TOKEN_FILE", "DATABASE_PASSWORD_FILE"]
)
def test_the_worker_refuses_to_start_without_its_configuration(tmp_path: Path, name: str) -> None:
    with pytest.raises(AutotradingError):
        create_worker_application(worker_configuration(tmp_path, **{name: ""}))


@pytest.mark.parametrize("content", ["not base64 at all!", "c2hvcnQ="], ids=["not-base64", "short-key"])
def test_the_worker_refuses_to_start_with_a_malformed_private_key(tmp_path: Path, content: str) -> None:
    configuration = worker_configuration(tmp_path)
    Path(configuration["CREDENTIALS_PRIVATE_KEY_FILE"]).write_text(content, encoding="utf-8")

    with pytest.raises(InvalidPrivateCredentialsKeyError):
        create_worker_application(configuration)


@pytest.mark.parametrize(
    ("network", "url"), [(ExchangeNetwork.TEST, TESTNET_API_URL), (ExchangeNetwork.REAL, MAINNET_API_URL)]
)
def test_the_exchange_network_follows_the_installation(network: ExchangeNetwork, url: str) -> None:
    assert {name: exchange.base_url for name, exchange in exchanges_for(network).items()} == {"Hyperliquid": url}


@pytest.mark.parametrize(
    ("network", "url"), [(ExchangeNetwork.TEST, TESTNET_API_URL), (ExchangeNetwork.REAL, MAINNET_API_URL)]
)
def test_the_tradable_assets_are_read_on_the_network_of_the_installation(network: ExchangeNetwork, url: str) -> None:
    assert {name: markets.base_url for name, markets in markets_for(network).items()} == {"Hyperliquid": url}


@pytest.mark.parametrize(
    ("network", "url"), [(ExchangeNetwork.TEST, TESTNET_API_URL), (ExchangeNetwork.REAL, MAINNET_API_URL)]
)
def test_the_orders_go_to_the_network_of_the_installation(network: ExchangeNetwork, url: str) -> None:
    assert {name: exchange.base_url for name, exchange in order_exchanges_for(network).items()} == {"Hyperliquid": url}


@pytest.mark.parametrize(
    ("network", "url"), [(ExchangeNetwork.TEST, TESTNET_API_URL), (ExchangeNetwork.REAL, MAINNET_API_URL)]
)
def test_the_activity_of_the_accounts_is_read_on_the_network_of_the_installation(
    network: ExchangeNetwork, url: str
) -> None:
    assert {name: reader.base_url for name, reader in activity_readers_for(network).items()} == {"Hyperliquid": url}


@pytest.mark.parametrize(
    ("configured", "percent"),
    [({}, Decimal(5)), ({SLIPPAGE_SETTING: "  "}, Decimal(5)), ({SLIPPAGE_SETTING: " 1.5 "}, Decimal("1.5"))],
    ids=["absent", "blank", "declared"],
)
def test_the_slippage_is_five_percent_unless_the_installation_declares_it(
    configured: dict[str, str], percent: Decimal
) -> None:
    assert slippage_from(configured) == Slippage.percent(percent)


@pytest.mark.parametrize("text", ["five", "NaN", "Infinity"])
def test_a_slippage_that_is_not_a_number_is_an_invalid_configuration(text: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        slippage_from({SLIPPAGE_SETTING: text})

    assert SLIPPAGE_SETTING in str(raised.value)


@pytest.mark.parametrize("text", ["0", "-1", "100", "250"])
def test_a_slippage_outside_its_range_is_refused(text: str) -> None:
    with pytest.raises(InvalidSlippageError):
        slippage_from({SLIPPAGE_SETTING: text})


def test_the_worker_refuses_to_start_with_an_invalid_slippage(tmp_path: Path) -> None:
    with pytest.raises(AutotradingError):
        create_worker_application(worker_configuration(tmp_path, **{SLIPPAGE_SETTING: "five"}))


def test_the_access_to_trade_is_opened_from_the_account_of_the_tenant() -> None:
    worker = Worker()
    account = worker.saved_account()
    credentials = worker.vault[account.credentials.ciphertext][2]
    accesses = OpenTradingAccessUseCase(
        InMemoryAccountRepositoryAdapter(worker.store, account.tenant_id), FakeCredentialOpenerAdapter(worker.vault)
    )

    assert accesses.execute(OpenTradingAccessCommand(account.id.value)) == TradingAccess(
        "Hyperliquid", credentials.account_address, credentials.secret_key
    )


def test_an_account_of_another_tenant_gives_no_access_to_trade() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())
    opener = FakeCredentialOpenerAdapter(worker.vault)
    accesses = OpenTradingAccessUseCase(InMemoryAccountRepositoryAdapter(worker.store, TenantId.new()), opener)

    with pytest.raises(OrderAccountNotFoundError):
        accesses.execute(OpenTradingAccessCommand(theirs.id.value))

    assert opener.opened_accesses == []


def test_each_tenant_gets_worker_use_cases_bound_to_it() -> None:
    accounts = exchanges_for(ExchangeNetwork.TEST)
    exchanges = WorkerExchanges(
        accounts,
        order_exchanges_for(ExchangeNetwork.TEST),
        activity_readers_for(ExchangeNetwork.TEST),
        executions_readers_for(ExchangeNetwork.TEST),
        accounts,
    )
    opener = SodiumCredentialOpenerAdapter({})
    settings = WorkerSettings("dev", Slippage.default())
    factory = worker_use_cases(create_engine("sqlite://"), opener, exchanges, settings, FakeMessengerAdapter())

    first, second = factory(TenantId.new()), factory(TenantId.new())

    assert first.close_exchange_position is not second.close_exchange_position
    assert first.read_exchange_state is not second.read_exchange_state
    assert first.run_exchange_verification is not second.run_exchange_verification


def test_the_close_is_asked_to_the_worker_for_the_tenant_and_the_user(tmp_path: Path) -> None:
    asked: list[httpx.Request] = []

    def worker_answer(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return httpx.Response(503, json={"detail": "exchange non raggiungibile"})

    configuration = installation_configuration(tmp_path)
    public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
    worker = worker_adapters("http://worker:8000", WORKER_TOKEN, httpx.MockTransport(worker_answer))
    factory = tenant_use_cases(
        create_engine("sqlite://"),
        PublicCredentialsKey(public_key, 1),
        ApiExchanges({}, {}),
        worker,
        httpx.Client(),
    )
    tenant_id, account_id = TenantId.new(), uuid4()

    with pytest.raises(OrderExchangeUnavailableError):
        factory(tenant_id).close_position.execute(ClosePositionCommand(account_id, "BTC", UserId("oid-anna")))

    assert [request.url.path for request in asked] == [
        f"/tenants/{tenant_id.value}/accounts/{account_id}/positions/BTC/close"
    ]
    assert asked[0].headers["Authorization"] == f"Bearer {WORKER_TOKEN}"


def test_the_procedure_is_asked_to_the_worker_for_the_tenant_and_the_user(tmp_path: Path) -> None:
    asked: list[httpx.Request] = []

    def worker_answer(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return httpx.Response(404, json={"detail": "non trovato"})

    configuration = installation_configuration(tmp_path)
    public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
    worker = worker_adapters("http://worker:8000", WORKER_TOKEN, httpx.MockTransport(worker_answer))
    factory = tenant_use_cases(
        create_engine("sqlite://"),
        PublicCredentialsKey(public_key, 1),
        ApiExchanges({}, {}),
        worker,
        httpx.Client(),
    )
    tenant_id, account_id = TenantId.new(), uuid4()

    with pytest.raises(VerificationAccountNotFoundError):
        factory(tenant_id).run_verification.execute(RunVerificationCommand(account_id, UserId("oid-anna")))

    assert [request.url.path for request in asked] == [
        f"/tenants/{tenant_id.value}/accounts/{account_id}/verifications"
    ]


def test_every_provider_of_the_catalog_has_a_way_to_verify_its_keys() -> None:
    assert {provider.value for provider in MODEL_CATALOG.providers} <= set(KEY_CHECKS)


def test_the_key_of_a_provider_is_verified_at_the_provider_for_the_tenant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderKeyStore()
    monkeypatch.setattr(
        bootstrap,
        "SqlAlchemyProviderKeyRepositoryAdapter",
        lambda _, tenant: InMemoryProviderKeyRepositoryAdapter(store, tenant),
    )
    asked: list[httpx.Request] = []

    def provider_answer(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    configuration = installation_configuration(tmp_path)
    public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
    worker = worker_adapters("http://worker:8000", WORKER_TOKEN)
    providers = httpx.Client(transport=httpx.MockTransport(provider_answer))
    factory = tenant_use_cases(
        create_engine("sqlite://"), PublicCredentialsKey(public_key, 1), ApiExchanges({}, {}), worker, providers
    )

    with pytest.raises(ProviderRejectedKeyError):
        factory(TenantId.new()).register_provider_key.execute(RegisterProviderKeyCommand("openrouter", "K-MADE-UP"))

    assert [str(request.url) for request in asked] == ["https://openrouter.ai/api/v1/key"]
    assert store.keys == []


def test_the_api_notifies_stops_and_manual_closings_with_the_same_notice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    notices: list[PositionClosedNoticePort] = []
    real_stop_ports, real_manual_closing = StopPorts, RecordManualClosingUseCase

    def stop_ports(
        cycles: RunningCyclePort,
        positions: FlowPositionsPort,
        openings: FlowOpeningsPort,
        closed_positions: ClosedPositionRepositoryPort,
        closing_notice: PositionClosedNoticePort,
    ) -> StopPorts:
        notices.append(closing_notice)
        return real_stop_ports(cycles, positions, openings, closed_positions, closing_notice)

    def manual_closing(
        flows: FlowRepositoryPort,
        openings: FlowOpeningsPort,
        closed_positions: ClosedPositionRepositoryPort,
        notice: PositionClosedNoticePort,
    ) -> RecordManualClosingUseCase:
        notices.append(notice)
        return real_manual_closing(flows, openings, closed_positions, notice)

    monkeypatch.setattr(bootstrap, "StopPorts", stop_ports)
    monkeypatch.setattr(bootstrap, "RecordManualClosingUseCase", manual_closing)
    configuration = installation_configuration(tmp_path)
    public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
    worker = worker_adapters("http://worker:8000", WORKER_TOKEN)
    factory = tenant_use_cases(
        create_engine("sqlite://"), PublicCredentialsKey(public_key, 1), ApiExchanges({}, {}), worker, httpx.Client()
    )

    factory(TenantId.new())

    assert len(notices) == 2
    assert all(isinstance(notice, NotifyPositionClosedUseCase) for notice in notices)
    assert notices[0] is notices[1]
