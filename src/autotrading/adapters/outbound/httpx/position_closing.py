from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
)
from autotrading.application.orders.outcome import OrderOutcome
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.rejection import RejectionReason
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

# A close waits for the exchange, its fills and possibly a lookup by client order id: more than a read.
TIMEOUT_SECONDS = 40.0


class HttpxPositionClosingAdapter:
    """Asks the worker, over the internal network of the installation, to close a position (ADR 0023).

    Bound to the tenant of the request. The answers of the worker become the errors of the port again; anything
    the worker cannot answer, or answers in an unexpected shape, is a worker that is not available.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"HttpxPositionClosingAdapter(tenant_id={self._tenant_id.value})"

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        path = f"/tenants/{self._tenant_id.value}/accounts/{account_id}/positions/{coin}/close"
        try:
            response = self._client.post(
                path,
                json={"user_id": user_id.value},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise OrderWorkerUnavailableError from error
        _raise_for_refusal(response.status_code, coin)
        return _outcome_of(response)


def _raise_for_refusal(status: int, coin: str) -> None:
    if status == httpx.codes.OK:
        return
    if status == httpx.codes.NOT_FOUND:
        raise OrderAccountNotFoundError
    if status == httpx.codes.CONFLICT:
        raise NoOpenPositionError(coin)
    if status == httpx.codes.SERVICE_UNAVAILABLE:
        raise OrderExchangeUnavailableError
    raise OrderWorkerUnavailableError


def _outcome_of(response: httpx.Response) -> OrderOutcome:
    try:
        body = response.json()
        return OrderOutcome(
            order_id=UUID(body["order_id"]),
            status=OrderStatus(body["status"]),
            coin=str(body["coin"]),
            filled_size=_decimal(body["filled_size"]),
            average_price=_decimal(body["average_price"]),
            fee=_decimal(body["fee"]),
            realized_pnl=_decimal(body["realized_pnl"]),
            executed_at=None if body["executed_at"] is None else datetime.fromisoformat(body["executed_at"]),
            reason=None if body["reason"] is None else RejectionReason(body["reason"]),
            exchange_message=body["exchange_message"],
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise OrderWorkerUnavailableError from error


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(value)
