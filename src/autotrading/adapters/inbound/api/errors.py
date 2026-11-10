from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from autotrading.domain.errors import AutotradingError


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
    AuthenticationNotConfiguredError: 503,
    IdentityProviderUnavailableError: 503,
}

_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def install_error_responses(api: FastAPI) -> None:
    for error_type in ERROR_STATUS:
        api.add_exception_handler(error_type, _respond)


async def _respond(_: Request, error: Exception) -> JSONResponse:
    status = next(status for error_type, status in ERROR_STATUS.items() if isinstance(error, error_type))
    headers = _CHALLENGE if status == 401 else None
    return JSONResponse({"detail": str(error)}, status_code=status, headers=headers)
