from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.ports import ReadAccountActivityCommand
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition, BalanceMovement
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

    def execute(self, command: ReadAccountActivityCommand) -> AccountActivity:
        path = f"/tenants/{self._tenant_id.value}/accounts/{command.account_id}/activity"
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


def _movement_of(movement: Mapping[str, Any]) -> BalanceMovement:
    return BalanceMovement(
        str(movement["movement_id"]), Decimal(movement["amount"]), datetime.fromisoformat(movement["moved_at"])
    )
