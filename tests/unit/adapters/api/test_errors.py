import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.errors import (
    AuthenticationNotConfiguredError,
    IdentityProviderUnavailableError,
    NotAuthenticatedError,
    UserRoleMissingError,
    install_error_responses,
)
from autotrading.domain.errors import AutotradingError


def client_raising(error: AutotradingError) -> TestClient:
    api = FastAPI()
    install_error_responses(api)

    @api.get("/fails")
    def fail() -> None:
        raise error

    return TestClient(api)


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (NotAuthenticatedError(), 401, "non autenticato"),
        (UserRoleMissingError(), 403, "ruolo Utente assente"),
        (AuthenticationNotConfiguredError(), 503, "autenticazione non configurata"),
        (IdentityProviderUnavailableError(), 503, "directory non raggiungibile"),
    ],
)
def test_each_typed_error_becomes_its_status_with_the_reason(error: AutotradingError, status: int, detail: str) -> None:
    response = client_raising(error).get("/fails")

    assert (response.status_code, response.json()) == (status, {"detail": detail})


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
