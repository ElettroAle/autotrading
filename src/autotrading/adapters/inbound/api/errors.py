import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from autotrading.domain.errors import AutotradingError

PROBLEM_MEDIA_TYPE = "application/problem+json"
INTERNAL_ERROR_DETAIL = "errore interno"
NOT_IMPLEMENTED_DETAIL = "non implementato"
INVALID_REQUEST_DETAIL = "richiesta non valida"
TRACE_PARENT = re.compile(r"^[0-9a-f]{2}-(?P<trace_id>[0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")
INVALID_TRACE_ID = "0" * 32

_CHALLENGE = {"WWW-Authenticate": "Bearer"}

errors_log = logging.getLogger("autotrading.api.errors")


class AuthenticationNotConfiguredError(AutotradingError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("autenticazione non configurata")


def install_error_responses(api: FastAPI) -> None:
    """One handler per kind of failure, every answer in Problem Details (RFC 9457, ADR 0027)."""
    api.add_exception_handler(AutotradingError, _respond_to_typed_error)
    api.add_exception_handler(RequestValidationError, _respond_to_invalid_request)
    api.add_exception_handler(NotImplementedError, _respond_to_not_implemented)
    api.add_exception_handler(Exception, _respond_to_unexpected_error)


@dataclass(frozen=True, slots=True)
class Correlation:
    request_id: str
    trace_id: str

    @classmethod
    def of(cls, request: Request) -> Correlation:
        return cls(uuid4().hex, _trace_id(request.headers.get("traceparent", "")))


async def _respond_to_typed_error(request: Request, error: Exception) -> JSONResponse:
    typed = cast(AutotradingError, error)
    headers = _CHALLENGE if typed.status_code == HTTPStatus.UNAUTHORIZED else None
    return _problem(Correlation.of(request), typed.status_code, str(typed), typed.details, headers)


async def _respond_to_invalid_request(request: Request, error: Exception) -> JSONResponse:
    # The framework would echo the input; a request may carry credentials, so only where and why are kept (R0.2.3).
    found = [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in cast(RequestValidationError, error).errors()
    ]
    return _problem(Correlation.of(request), HTTPStatus.UNPROCESSABLE_ENTITY, INVALID_REQUEST_DETAIL, {"errors": found})


async def _respond_to_not_implemented(request: Request, _: Exception) -> JSONResponse:
    return _problem(Correlation.of(request), HTTPStatus.NOT_IMPLEMENTED, NOT_IMPLEMENTED_DETAIL)


async def _respond_to_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    correlation = Correlation.of(request)
    errors_log.error(
        "unexpected error, request %s, trace %s", correlation.request_id, correlation.trace_id, exc_info=error
    )
    return _problem(correlation, HTTPStatus.INTERNAL_SERVER_ERROR, INTERNAL_ERROR_DETAIL)


def _problem(
    correlation: Correlation,
    status: int,
    detail: str,
    details: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        **(details or {}),
        "requestId": correlation.request_id,
        "traceId": correlation.trace_id,
    }
    return JSONResponse(body, status_code=status, headers=headers, media_type=PROBLEM_MEDIA_TYPE)


def _trace_id(traceparent: str) -> str:
    """The trace of the caller when it sends a valid W3C trace context, otherwise a new one."""
    match = TRACE_PARENT.match(traceparent)
    if match and match["trace_id"] != INVALID_TRACE_ID:
        return match["trace_id"]
    return uuid4().hex
