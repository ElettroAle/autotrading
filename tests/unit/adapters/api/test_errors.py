from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from autotrading.adapters.inbound.api.errors import (
    PROBLEM_MEDIA_TYPE,
    AuthenticationNotConfiguredError,
    IdentityProviderUnavailableError,
    NotAuthenticatedError,
    UserRoleMissingError,
    install_error_responses,
)
from autotrading.application.accounts.errors import (
    AccountNameInUseError,
    AccountNotFoundError,
    CredentialsNotOpenedError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    UnsupportedExchangeError,
    WorkerUnavailableError,
)
from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
    UnsupportedOrderExchangeError,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.application.verification.errors import (
    VerificationAccountNotFoundError,
    VerificationStepError,
    VerificationWorkerUnavailableError,
)
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.errors import (
    AccountNameRequiredError,
    CredentialsOfAnotherAccountError,
    CredentialsRequiredError,
    ExchangeRequiredError,
    OpenPositionsNeedConfirmationError,
)
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.errors import InvalidLeverageError, ManualOpeningNotAllowedError
from autotrading.domain.verification.errors import InsufficientMarginError, PositionAlreadyOpenError

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
STANDARD_MEMBERS = {"type", "title", "status", "requestId", "traceId"}


class Payload(BaseModel):
    secret_key: str


def client_raising(error: BaseException) -> TestClient:
    api = FastAPI()
    install_error_responses(api)

    @api.get("/fails")
    def fail() -> None:
        raise error

    @api.post("/validates")
    def validate(payload: Payload) -> None:
        del payload

    return TestClient(api, raise_server_exceptions=False)


def reason_of(problem: dict[str, object]) -> dict[str, object]:
    return {name: value for name, value in problem.items() if name not in STANDARD_MEMBERS}


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotAuthenticatedError(), 401),
        (UserRoleMissingError(), 403),
        (CrossTenantAccessError(), 404),
        (AccountNotFoundError(), 404),
        (OrderAccountNotFoundError(), 404),
        (ManualOpeningNotAllowedError(), 403),
        (NoOpenPositionError("ETH"), 409),
        (VerificationAccountNotFoundError(), 404),
        (PositionAlreadyOpenError("BTC"), 409),
        (InsufficientMarginError(Decimal(10), "USDC"), 409),
        (UnsupportedOrderExchangeError("Binance", ["Hyperliquid"]), 422),
        (AccountNameInUseError(AccountName("test-1")), 409),
        (OpenPositionsNeedConfirmationError(), 409),
        (AccountNameRequiredError(), 422),
        (ExchangeRequiredError(), 422),
        (CredentialsRequiredError(), 422),
        (CredentialsOfAnotherAccountError(), 422),
        (UnsupportedExchangeError(ExchangeName("Binance"), ["Hyperliquid"]), 422),
        (ExchangeRejectedCredentialsError("refused"), 422),
        (AuthenticationNotConfiguredError(), 503),
        (IdentityProviderUnavailableError(), 503),
        (ExchangeUnavailableError(), 503),
        (WorkerUnavailableError(), 503),
        (OrderExchangeUnavailableError(), 503),
        (OrderWorkerUnavailableError(), 503),
        (VerificationStepError("timeout"), 503),
        (VerificationWorkerUnavailableError(), 503),
        (CredentialsNotOpenedError(), 500),
        (InvalidLeverageError(0), 400),
    ],
    ids=lambda value: type(value).__name__ if isinstance(value, BaseException) else str(value),
)
def test_each_typed_error_is_answered_with_the_status_it_declares(error: AutotradingError, status: int) -> None:
    response = client_raising(error).get("/fails")

    assert (response.status_code, response.json()["status"], response.json()["detail"]) == (status, status, str(error))


def test_a_typed_error_is_answered_as_problem_details() -> None:
    response = client_raising(NoOpenPositionError("ETH")).get("/fails")

    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert {name: response.json()[name] for name in ("type", "title", "status", "detail")} == {
        "type": "about:blank",
        "title": "Conflict",
        "status": 409,
        "detail": "nessuna posizione aperta su ETH",
    }


def test_every_problem_carries_a_request_id_and_a_trace_id() -> None:
    first = client_raising(AccountNotFoundError()).get("/fails").json()
    second = client_raising(AccountNotFoundError()).get("/fails").json()

    assert len({first["requestId"], second["requestId"]}) == 2
    assert all(len(problem["traceId"]) == 32 for problem in (first, second))


def test_the_trace_id_follows_the_trace_context_of_the_caller() -> None:
    headers = {"traceparent": f"00-{TRACE_ID}-00f067aa0ba902b7-01"}

    response = client_raising(AccountNotFoundError()).get("/fails", headers=headers)

    assert response.json()["traceId"] == TRACE_ID


@pytest.mark.parametrize("traceparent", ["00-not-hex-01", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", "garbage"])
def test_an_invalid_trace_context_is_replaced_by_a_new_trace_id(traceparent: str) -> None:
    response = client_raising(AccountNotFoundError()).get("/fails", headers={"traceparent": traceparent})

    trace_id = response.json()["traceId"]
    assert (len(trace_id), trace_id in traceparent) == (32, False)


@pytest.mark.parametrize(
    ("error", "details"),
    [
        (UnsupportedExchangeError(ExchangeName("Binance"), ["Hyperliquid"]), {"supported": ["Hyperliquid"]}),
        (UnsupportedOrderExchangeError("Binance", ["Hyperliquid"]), {"supported": ["Hyperliquid"]}),
        (ExchangeRejectedCredentialsError("refused"), {"exchange_message": "refused"}),
    ],
)
def test_an_error_adds_its_details_to_the_problem(error: AutotradingError, details: dict[str, object]) -> None:
    response = client_raising(error).get("/fails")

    assert reason_of(response.json()) == {"detail": str(error), **details}


def test_a_not_found_and_another_tenant_read_the_same() -> None:
    answers = [client_raising(error).get("/fails") for error in (AccountNotFoundError(), CrossTenantAccessError())]

    assert [(answer.status_code, reason_of(answer.json())) for answer in answers] == [
        (404, {"detail": "non trovato"}),
        (404, {"detail": "non trovato"}),
    ]


def test_only_an_unauthenticated_answer_asks_for_a_bearer_token() -> None:
    challenges = {
        type(error).__name__: client_raising(error).get("/fails").headers.get("WWW-Authenticate")
        for error in (NotAuthenticatedError(), UserRoleMissingError(), AuthenticationNotConfiguredError())
    }

    assert challenges == {
        "NotAuthenticatedError": "Bearer",
        "UserRoleMissingError": None,
        "AuthenticationNotConfiguredError": None,
    }


def test_an_unexpected_error_is_an_internal_error_that_reveals_nothing() -> None:
    response = client_raising(LookupError("secret detail")).get("/fails")

    assert (response.status_code, response.headers["content-type"]) == (500, PROBLEM_MEDIA_TYPE)
    assert reason_of(response.json()) == {"detail": "errore interno"}


def test_a_capability_not_implemented_is_answered_as_such() -> None:
    response = client_raising(NotImplementedError("later")).get("/fails")

    assert (response.status_code, reason_of(response.json())) == (501, {"detail": "non implementato"})


def test_an_invalid_request_names_where_and_why_but_never_echoes_the_input() -> None:
    response = client_raising(AccountNotFoundError()).post("/validates", json={"secret_key": 7})

    problem = response.json()
    assert (response.status_code, response.headers["content-type"]) == (422, PROBLEM_MEDIA_TYPE)
    assert problem["detail"] == "richiesta non valida"
    assert [error["loc"] for error in problem["errors"]] == [["body", "secret_key"]]
    assert "7" not in str(problem["errors"])
