from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TypedDict
from uuid import UUID

import httpx

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

SHAPE_ERRORS = (KeyError, TypeError, ValueError, InvalidOperation)

# The worker reads the activity and the transfers of the account on the exchange within the window.
TIMEOUT_SECONDS = 30.0


class _PositionBody(TypedDict):
    asset: str
    side: str
    size: str
    margin: str
    unrealized_pnl: str
    leverage: int
    entry_price: str
    mark_price: str


class _TransferBody(TypedDict):
    transferred_at: str
    amount: str
    direction: str


class _ActivityBody(TypedDict):
    """What the worker answers; its shape is checked while it is read, a wrong one is a shape error."""

    currency: str
    balance: str
    available_margin: str
    positions: list[_PositionBody]
    read_at: str


class WorkerAccountActivityAdapter:
    """Asks the worker, over the internal network of the installation, what the exchange shows of an account: its
    activity, and the deposits and withdrawals of its history of the capital (ADR storico-delle-variazioni-di-capitale).

    Bound to the tenant of the request (ADR 0021, ADR 0044). An account the worker does not find is not found; any
    other answer it cannot give, or gives in an unexpected shape, is an exchange that cannot be read now.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"WorkerAccountActivityAdapter(tenant_id={self._tenant_id.value})"

    def execute(self, account_id: UUID) -> AccountActivity:
        response = self._answer(f"/accounts/{account_id}/activity", {})
        try:
            return _activity_of(response.json())
        except SHAPE_ERRORS as error:
            raise FlowExchangeUnavailableError from error

    def transfers(self, account_id: UUID, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        bounds = {"since": window.since, "until": window.until}
        params = {name: bound.isoformat() for name, bound in bounds.items() if bound is not None}
        response = self._answer(f"/accounts/{account_id}/transfers", params)
        try:
            return tuple(_transfer_of(transfer) for transfer in response.json())
        except SHAPE_ERRORS as error:
            raise FlowExchangeUnavailableError from error

    def _answer(self, path: str, params: dict[str, str]) -> httpx.Response:
        """The answer of the worker on the account of the tenant, only when the worker could give it."""
        try:
            response = self._client.get(
                f"/tenants/{self._tenant_id.value}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise FlowExchangeUnavailableError from error
        if response.status_code == httpx.codes.NOT_FOUND:
            raise FlowAccountNotFoundError
        if response.status_code != httpx.codes.OK:
            raise FlowExchangeUnavailableError
        return response


def _activity_of(body: _ActivityBody) -> AccountActivity:
    return AccountActivity(
        currency=str(body["currency"]),
        balance=Decimal(body["balance"]),
        available_margin=Decimal(body["available_margin"]),
        positions=tuple(_position_of(position) for position in body["positions"]),
        read_at=datetime.fromisoformat(body["read_at"]),
    )


def _position_of(position: _PositionBody) -> AccountPosition:
    return AccountPosition(
        asset=str(position["asset"]),
        side=TradeSide(position["side"]),
        size=Decimal(position["size"]),
        margin=Decimal(position["margin"]),
        unrealized_pnl=Decimal(position["unrealized_pnl"]),
        leverage=int(position["leverage"]),
        entry_price=Decimal(position["entry_price"]),
        mark_price=Decimal(position["mark_price"]),
    )


def _transfer_of(transfer: _TransferBody) -> AccountTransfer:
    return AccountTransfer(
        datetime.fromisoformat(transfer["transferred_at"]),
        Decimal(transfer["amount"]),
        TransferDirection(transfer["direction"]),
    )
