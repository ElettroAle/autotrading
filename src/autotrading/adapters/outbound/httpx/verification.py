from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from autotrading.application.verification.errors import (
    VerificationAccountNotFoundError,
    VerificationStepError,
    VerificationWorkerUnavailableError,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.errors import VerificationNotStartedError
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import Step
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.step_outcome import StepOutcome
from autotrading.domain.verification.verification_run import VerificationRun

# About ten calls to the exchange, each allowed up to 10 seconds (ADR 0024).
TIMEOUT_SECONDS = 120.0
SHAPE_ERRORS = (KeyError, TypeError, ValueError, InvalidOperation)


class HttpxVerificationAdapter:
    """Asks the worker, over the internal network of the installation, to run the procedure (ADR 0024).

    Bound to the tenant of the request. The answers of the worker become the errors of the port again; anything
    the worker cannot answer, or answers in an unexpected shape, is a worker that is not available.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"HttpxVerificationAdapter(tenant_id={self._tenant_id.value})"

    def run(self, account_id: UUID, user_id: UserId) -> VerificationRun:
        path = f"/tenants/{self._tenant_id.value}/accounts/{account_id}/verifications"
        try:
            response = self._client.post(
                path,
                json={"user_id": user_id.value},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise VerificationWorkerUnavailableError from error
        _raise_for_refusal(response)
        return _run_of(response)


def _raise_for_refusal(response: httpx.Response) -> None:
    status = response.status_code
    if status == httpx.codes.OK:
        return
    if status == httpx.codes.NOT_FOUND:
        raise VerificationAccountNotFoundError
    detail = _detail(response)
    if status == httpx.codes.CONFLICT and detail is not None:
        raise VerificationNotStartedError(detail)
    if status == httpx.codes.SERVICE_UNAVAILABLE and detail is not None:
        raise VerificationStepError(detail)
    raise VerificationWorkerUnavailableError


def _detail(response: httpx.Response) -> str | None:
    try:
        detail = response.json()["detail"]
    except (*SHAPE_ERRORS, AttributeError):
        return None
    return detail if isinstance(detail, str) else None


def _run_of(response: httpx.Response) -> VerificationRun:
    try:
        body = response.json()
        return VerificationRun(
            id=UUID(body["id"]),
            account_id=UUID(body["account_id"]),
            user_id=str(body["user_id"]),
            environment=str(body["environment"]),
            started_at=datetime.fromisoformat(body["started_at"]),
            steps=tuple(_step_of(step) for step in body["steps"]),
        )
    except SHAPE_ERRORS as error:
        raise VerificationWorkerUnavailableError from error


def _step_of(body: Any) -> StepOutcome:
    reading, order = body["reading"], body["order"]
    return StepOutcome(
        step=Step(body["step"]),
        succeeded=bool(body["succeeded"]),
        message=body["message"],
        reading=None if reading is None else _reading_of(reading),
        order=None if order is None else _order_of(order),
    )


def _reading_of(body: Any) -> AccountReading:
    return AccountReading(
        balance=Decimal(body["balance"]),
        available_margin=Decimal(body["available_margin"]),
        currency=str(body["currency"]),
        positions=tuple(
            PositionReading(str(item["coin"]), str(item["side"]), Decimal(item["size"]), int(item["leverage"]))
            for item in body["positions"]
        ),
    )


def _order_of(body: Any) -> OrderResult:
    return OrderResult(
        succeeded=bool(body["succeeded"]),
        fee=Decimal(body["fee"]),
        realized_pnl=Decimal(body["realized_pnl"]),
        message=body["message"],
    )
