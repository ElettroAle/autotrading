from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TypedDict, cast

import httpx

from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    WorkerUnavailableError,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.tenancy.tenant_id import TenantId

TIMEOUT_SECONDS = 15.0


class _AmountBody(TypedDict):
    amount: str
    currency: str


class _PositionBody(TypedDict):
    coin: str
    side: str
    size: str
    leverage: int
    entry_price: str
    unrealized_pnl: str
    liquidation_price: str | None


class _StateBody(TypedDict):
    """What the worker answers for a state; its shape is checked while it is read, a wrong one is a shape error."""

    balance: _AmountBody
    available_margin: _AmountBody
    positions: list[_PositionBody]
    read_at: str


class HttpxAccountStateAdapter:
    """Asks the worker, over the internal network of the installation, for the state of an account (ADR 0021).

    Bound to the tenant of the request. The answers of the worker become the errors of the port again; anything
    the worker cannot answer, or answers in an unexpected shape, is a worker that is not available.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"HttpxAccountStateAdapter(tenant_id={self._tenant_id.value})"

    def read_state(self, account_id: AccountId) -> AccountState:
        path = f"/tenants/{self._tenant_id.value}/accounts/{account_id.value}/state"
        try:
            response = self._client.get(path, headers={"Authorization": f"Bearer {self._token}"})
        except httpx.HTTPError as error:
            raise WorkerUnavailableError from error
        return _state_of(_body_of(response), response.status_code)


def _body_of(response: httpx.Response) -> Mapping[str, object]:
    try:
        body = response.json()
    except ValueError as error:
        raise WorkerUnavailableError from error
    if not isinstance(body, Mapping):
        raise WorkerUnavailableError
    return body


def _state_of(body: Mapping[str, object], status: int) -> AccountState:
    _raise_for_refusal(body, status)
    state = cast("_StateBody", body)
    try:
        return AccountState(
            balance=_balance_of(state["balance"]),
            available_margin=_balance_of(state["available_margin"]),
            positions=tuple(_position_of(position) for position in state["positions"]),
            read_at=datetime.fromisoformat(state["read_at"]),
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise WorkerUnavailableError from error


def _raise_for_refusal(body: Mapping[str, object], status: int) -> None:
    if status == httpx.codes.OK:
        return
    if status == httpx.codes.NOT_FOUND:
        raise AccountNotFoundError
    if status == httpx.codes.UNPROCESSABLE_ENTITY and "exchange_message" in body:
        raise ExchangeRejectedCredentialsError(str(body["exchange_message"]))
    if status == httpx.codes.SERVICE_UNAVAILABLE:
        raise ExchangeUnavailableError
    raise WorkerUnavailableError


def _balance_of(amount: _AmountBody) -> Balance:
    return Balance(Decimal(amount["amount"]), str(amount["currency"]))


def _position_of(position: _PositionBody) -> Position:
    liquidation = position["liquidation_price"]
    return Position(
        coin=str(position["coin"]),
        side=PositionSide(position["side"]),
        size=Decimal(position["size"]),
        leverage=int(position["leverage"]),
        entry_price=Decimal(position["entry_price"]),
        unrealized_pnl=Decimal(position["unrealized_pnl"]),
        liquidation_price=None if liquidation is None else Decimal(liquidation),
    )
