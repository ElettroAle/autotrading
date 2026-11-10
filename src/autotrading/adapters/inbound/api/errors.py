from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
from autotrading.domain.accounts.errors import (
    AccountNameRequiredError,
    CredentialsOfAnotherAccountError,
    CredentialsRequiredError,
    ExchangeRequiredError,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.errors import ManualOpeningNotAllowedError
from autotrading.domain.verification.errors import VerificationNotStartedError


class NotAuthenticatedError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("non autenticato")


class UserRoleMissingError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("ruolo Utente assente")


class AuthenticationNotConfiguredError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("autenticazione non configurata")


class IdentityProviderUnavailableError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("directory non raggiungibile")


# The single map from typed error to HTTP status (rule tech-fastapi). An error missing here is a defect.
ERROR_STATUS: dict[type[AutotradingError], int] = {
    NotAuthenticatedError: 401,
    UserRoleMissingError: 403,
    CrossTenantAccessError: 404,
    AccountNotFoundError: 404,
    OrderAccountNotFoundError: 404,
    ManualOpeningNotAllowedError: 403,
    NoOpenPositionError: 409,
    VerificationAccountNotFoundError: 404,
    VerificationNotStartedError: 409,
    UnsupportedOrderExchangeError: 422,
    AccountNameInUseError: 409,
    AccountNameRequiredError: 422,
    ExchangeRequiredError: 422,
    CredentialsRequiredError: 422,
    CredentialsOfAnotherAccountError: 422,
    UnsupportedExchangeError: 422,
    ExchangeRejectedCredentialsError: 422,
    AuthenticationNotConfiguredError: 503,
    IdentityProviderUnavailableError: 503,
    ExchangeUnavailableError: 503,
    WorkerUnavailableError: 503,
    OrderExchangeUnavailableError: 503,
    OrderWorkerUnavailableError: 503,
    # The account could not be read before the procedure started: the exchange or the credentials failed.
    VerificationStepError: 503,
    VerificationWorkerUnavailableError: 503,
    # Sealed credentials that do not open are a fault of the installation, never of the request.
    CredentialsNotOpenedError: 500,
}


def _supported(error: Any) -> dict[str, Any]:
    return {"supported": list(error.supported)}


def _exchange_message(error: Any) -> dict[str, Any]:
    return {"exchange_message": error.exchange_message}


# What an answer adds to the reason, for the errors whose outcome the requirement asks to show.
ERROR_DETAILS: dict[type[AutotradingError], Callable[[Any], dict[str, Any]]] = {
    UnsupportedExchangeError: _supported,
    UnsupportedOrderExchangeError: _supported,
    ExchangeRejectedCredentialsError: _exchange_message,
}

_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def install_error_responses(api: FastAPI) -> None:
    for error_type in ERROR_STATUS:
        api.add_exception_handler(error_type, _respond)
    api.add_exception_handler(RequestValidationError, _respond_to_invalid_request)


async def _respond(_: Request, error: Exception) -> JSONResponse:
    status = next(status for error_type, status in ERROR_STATUS.items() if isinstance(error, error_type))
    headers = _CHALLENGE if status == 401 else None
    body: dict[str, Any] = {"detail": str(error)}
    for error_type, details in ERROR_DETAILS.items():
        if isinstance(error, error_type):
            body.update(details(error))
    return JSONResponse(body, status_code=status, headers=headers)


async def _respond_to_invalid_request(_: Request, error: Exception) -> JSONResponse:
    # The framework would echo the input; a request may carry credentials, so only where and why are kept (R0.2.3).
    errors = error.errors() if isinstance(error, RequestValidationError) else []
    detail = [{"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]} for item in errors]
    return JSONResponse({"detail": detail}, status_code=422)
