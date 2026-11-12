from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity, AccountFill
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind

OUTSIDE_PLATFORM = "chiusa fuori dalla piattaforma"

type PlatformOrders = Mapping[UUID, FlowId | None]


@dataclass(frozen=True, slots=True)
class AccountReading:
    """What the last reconciliation of an account saw: when, and the assets each flow had open (R1.6.2)."""

    account_id: UUID
    read_at: datetime
    open_assets: Mapping[FlowId, frozenset[str]]


@dataclass(frozen=True, slots=True)
class OutsideClosing:
    """A position of a flow gone from the exchange without an order of the flow, with the outcome read there."""

    flow_id: FlowId
    asset: str
    reason: str
    realized_pnl: Decimal
    fee: Decimal
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class AccountReconciliation:
    """What a reading of the account shows that no flow explains, compared with the previous reading (R1.6.2).

    Without a previous reading, past executions and movements are the starting point, not something to report.
    """

    items: tuple[UnattributableItem, ...]
    closed_outside: tuple[OutsideClosing, ...]
    reading: AccountReading
    open_assets: frozenset[str]

    @classmethod
    def of(
        cls,
        account_id: UUID,
        flows_of_account: Iterable[Flow],
        activity: AccountActivity,
        orders: PlatformOrders,
        previous: AccountReading | None,
    ) -> AccountReconciliation:
        flows = [flow for flow in flows_of_account if flow.status != FlowStatus.ARCHIVED]
        since = None if previous is None else previous.read_at
        new_fills = () if since is None else tuple(fill for fill in activity.fills if fill.executed_at > since)
        reading = AccountReading(account_id, activity.read_at, _open_assets_of(flows, activity))
        return cls(
            items=(
                *_unowned_positions(account_id, flows, activity),
                *_unknown_fills(account_id, new_fills, orders, activity.read_at),
                *_balance_changes(account_id, activity, since),
            ),
            closed_outside=() if previous is None else _closed_outside(previous, reading, new_fills, orders, activity),
            reading=reading,
            open_assets=frozenset(position.asset for position in activity.positions),
        )


def _open_assets_of(flows: list[Flow], activity: AccountActivity) -> dict[FlowId, frozenset[str]]:
    open_assets = {position.asset for position in activity.positions}
    return {flow.id: frozenset(open_assets.intersection(flow.configuration.assets)) for flow in flows}


def _unowned_positions(account_id: UUID, flows: list[Flow], activity: AccountActivity) -> list[UnattributableItem]:
    owned = {asset for flow in flows for asset in flow.configuration.assets}
    return [
        UnattributableItem(
            account_id, UnattributableKind.POSITION, position.asset, position.asset, position.size, activity.read_at
        )
        for position in activity.positions
        if position.asset not in owned
    ]


def _unknown_fills(
    account_id: UUID, fills: tuple[AccountFill, ...], orders: PlatformOrders, read_at: datetime
) -> list[UnattributableItem]:
    return [
        UnattributableItem(account_id, UnattributableKind.FILL, fill.fill_id, fill.asset, fill.size, read_at)
        for fill in fills
        if not _of_platform(fill, orders)
    ]


def _balance_changes(account_id: UUID, activity: AccountActivity, since: datetime | None) -> list[UnattributableItem]:
    if since is None:
        return []
    return [
        UnattributableItem(
            account_id, UnattributableKind.BALANCE_CHANGE, movement.movement_id, None, movement.amount, activity.read_at
        )
        for movement in activity.movements
        if movement.moved_at > since
    ]


def _closed_outside(
    previous: AccountReading,
    reading: AccountReading,
    fills: tuple[AccountFill, ...],
    orders: PlatformOrders,
    activity: AccountActivity,
) -> tuple[OutsideClosing, ...]:
    return tuple(
        _outside_closing(flow_id, asset, fills, orders, activity)
        for flow_id, assets in previous.open_assets.items()
        if flow_id in reading.open_assets
        for asset in sorted(assets - reading.open_assets[flow_id])
        if not any(fill.asset == asset and _flow_of(fill, orders) == flow_id for fill in fills)
    )


def _outside_closing(
    flow_id: FlowId, asset: str, fills: tuple[AccountFill, ...], orders: PlatformOrders, activity: AccountActivity
) -> OutsideClosing:
    outside = [fill for fill in fills if fill.asset == asset and not _of_platform(fill, orders)]
    return OutsideClosing(
        flow_id=flow_id,
        asset=asset,
        reason=OUTSIDE_PLATFORM,
        realized_pnl=sum((fill.realized_pnl for fill in outside), Decimal(0)),
        fee=sum((fill.fee for fill in outside), Decimal(0)),
        closed_at=max((fill.executed_at for fill in outside), default=activity.read_at),
    )


def _of_platform(fill: AccountFill, orders: PlatformOrders) -> bool:
    return fill.order_id is not None and fill.order_id in orders


def _flow_of(fill: AccountFill, orders: PlatformOrders) -> FlowId | None:
    return None if fill.order_id is None else orders.get(fill.order_id)
