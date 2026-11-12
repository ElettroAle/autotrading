from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.flows.account_activity import AccountActivity, AccountFill, AccountPosition, BalanceMovement
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

SHAPE_ERRORS = (KeyError, TypeError, ValueError, InvalidOperation)


class HttpxAccountActivityAdapter:
    """Asks the worker, over the internal network of the installation, what the exchange shows of an account.

    Bound to the tenant of the request (ADR 0021, ADR 0044). An account the worker does not find is not found; any
    other answer it cannot give, or gives in an unexpected shape, is an exchange that cannot be read now.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"HttpxAccountActivityAdapter(tenant_id={self._tenant_id.value})"

    def activity(self, account_id: UUID) -> AccountActivity:
        path = f"/tenants/{self._tenant_id.value}/accounts/{account_id}/activity"
        try:
            response = self._client.get(path, headers={"Authorization": f"Bearer {self._token}"})
        except httpx.HTTPError as error:
            raise FlowExchangeUnavailableError from error
        if response.status_code == httpx.codes.NOT_FOUND:
            raise FlowAccountNotFoundError
        if response.status_code != httpx.codes.OK:
            raise FlowExchangeUnavailableError
        try:
            return _activity_of(response.json())
        except SHAPE_ERRORS as error:
            raise FlowExchangeUnavailableError from error


def _activity_of(body: Mapping[str, Any]) -> AccountActivity:
    return AccountActivity(
        currency=str(body["currency"]),
        balance=Decimal(body["balance"]),
        available_margin=Decimal(body["available_margin"]),
        positions=tuple(_position_of(position) for position in body["positions"]),
        fills=tuple(_fill_of(fill) for fill in body["fills"]),
        movements=tuple(_movement_of(movement) for movement in body["movements"]),
        read_at=datetime.fromisoformat(body["read_at"]),
    )


def _position_of(position: Mapping[str, Any]) -> AccountPosition:
    return AccountPosition(
        asset=str(position["asset"]),
        side=TradeSide(position["side"]),
        size=Decimal(position["size"]),
        margin=Decimal(position["margin"]),
        unrealized_pnl=Decimal(position["unrealized_pnl"]),
    )


def _fill_of(fill: Mapping[str, Any]) -> AccountFill:
    order_id = fill["order_id"]
    return AccountFill(
        fill_id=str(fill["fill_id"]),
        order_id=None if order_id is None else UUID(order_id),
        asset=str(fill["asset"]),
        size=Decimal(fill["size"]),
        price=Decimal(fill["price"]),
        fee=Decimal(fill["fee"]),
        realized_pnl=Decimal(fill["realized_pnl"]),
        executed_at=datetime.fromisoformat(fill["executed_at"]),
    )


def _movement_of(movement: Mapping[str, Any]) -> BalanceMovement:
    return BalanceMovement(
        str(movement["movement_id"]), Decimal(movement["amount"]), datetime.fromisoformat(movement["moved_at"])
    )
