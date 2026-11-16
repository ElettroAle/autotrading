from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import LedgerEntry
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind


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
    realized_pnl: Decimal
    fee: Decimal
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class ProtectionClosing:
    """A position of a flow closed by its stop loss or take profit on the exchange, with the outcome read from the
    execution (R3.1.2, ADR chiusure-per-protezione-nello-storico).
    """

    flow_id: FlowId
    asset: str
    reason: CloseReason
    realized_pnl: Decimal
    fee: Decimal
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class AccountReconciliation:
    """What a reading of the account shows that no flow explains, compared with the previous reading (R1.6.2).

    The executions are those the ledger has just recorded (ADR 0063). Without a previous reading, past executions and
    movements are the starting point, not something to report.
    """

    items: tuple[UnattributableItem, ...]
    closed_outside: tuple[OutsideClosing, ...]
    reading: AccountReading
    open_assets: frozenset[str]
    closed_by_protection: tuple[ProtectionClosing, ...] = ()

    @classmethod
    def of(
        cls,
        account_id: UUID,
        flows_of_account: Iterable[Flow],
        activity: AccountActivity,
        previous: AccountReading | None,
        recorded: tuple[LedgerEntry, ...],
    ) -> AccountReconciliation:
        flows = [flow for flow in flows_of_account if flow.status != FlowStatus.ARCHIVED]
        since = None if previous is None else previous.read_at
        new_entries = () if since is None else recorded
        reading = AccountReading(account_id, activity.read_at, _open_assets_of(flows, activity))
        return cls(
            items=(
                *_unowned_positions(account_id, flows, activity),
                *_unknown_fills(account_id, new_entries, activity.read_at),
                *_balance_changes(account_id, activity, since),
            ),
            closed_outside=() if previous is None else _closed_outside(previous, reading, new_entries, activity),
            reading=reading,
            open_assets=activity.open_assets,
            closed_by_protection=() if previous is None else _closed_by_protection(previous, reading, new_entries),
        )


def _open_assets_of(flows: list[Flow], activity: AccountActivity) -> dict[FlowId, frozenset[str]]:
    return {flow.id: activity.open_assets.intersection(flow.configuration.assets) for flow in flows}


def _unowned_positions(account_id: UUID, flows: list[Flow], activity: AccountActivity) -> list[UnattributableItem]:
    owned = {asset for flow in flows for asset in flow.configuration.assets}
    return [
        UnattributableItem(
            account_id, UnattributableKind.POSITION, position.asset, position.asset, position.size, activity.read_at
        )
        for position in activity.positions
        if position.asset not in owned
    ]


def _unknown_fills(account_id: UUID, entries: tuple[LedgerEntry, ...], read_at: datetime) -> list[UnattributableItem]:
    return [
        UnattributableItem(
            account_id,
            UnattributableKind.FILL,
            entry.execution.fill_id,
            entry.execution.asset,
            abs(entry.execution.size),
            read_at,
        )
        for entry in entries
        if not entry.platform_order
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
    entries: tuple[LedgerEntry, ...],
    activity: AccountActivity,
) -> tuple[OutsideClosing, ...]:
    # A closing by an order of the platform, the manual command and the protections included, is recorded by whoever
    # sent it, or as a closing by protection.
    return tuple(
        _outside_closing(flow_id, asset, entries, activity)
        for flow_id, asset in _gone(previous, reading)
        if not any(entry.execution.asset == asset and entry.platform_order for entry in entries)
    )


def _gone(previous: AccountReading, reading: AccountReading) -> list[tuple[FlowId, str]]:
    """The positions of the flows open at the previous reading and no longer open now."""
    return [
        (flow_id, asset)
        for flow_id, assets in previous.open_assets.items()
        if flow_id in reading.open_assets
        for asset in sorted(assets - reading.open_assets[flow_id])
    ]


def _closed_by_protection(
    previous: AccountReading, reading: AccountReading, entries: tuple[LedgerEntry, ...]
) -> tuple[ProtectionClosing, ...]:
    closings = (_protection_closing(flow_id, asset, entries) for flow_id, asset in _gone(previous, reading))
    return tuple(closing for closing in closings if closing is not None)


def _protection_closing(flow_id: FlowId, asset: str, entries: tuple[LedgerEntry, ...]) -> ProtectionClosing | None:
    executed = [
        (entry.execution, reason)
        for entry in entries
        if entry.execution.asset == asset and (reason := entry.protection) is not None
    ]
    if not executed:
        return None
    # The last protection executed closed what was left of the position.
    return ProtectionClosing(
        flow_id=flow_id,
        asset=asset,
        reason=executed[-1][1],
        realized_pnl=sum((execution.realized_pnl for execution, _ in executed), Decimal(0)),
        fee=sum((execution.fee for execution, _ in executed), Decimal(0)),
        closed_at=max(execution.executed_at for execution, _ in executed),
    )


def _outside_closing(
    flow_id: FlowId, asset: str, entries: tuple[LedgerEntry, ...], activity: AccountActivity
) -> OutsideClosing:
    outside = [entry.execution for entry in entries if entry.execution.asset == asset and not entry.platform_order]
    return OutsideClosing(
        flow_id=flow_id,
        asset=asset,
        realized_pnl=sum((execution.realized_pnl for execution in outside), Decimal(0)),
        fee=sum((execution.fee for execution in outside), Decimal(0)),
        closed_at=max((execution.executed_at for execution in outside), default=activity.read_at),
    )
