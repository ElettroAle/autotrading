from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import AccountLedger, LedgerEntry
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class AccountReading:
    """What the last reconciliation of an account saw: when, the assets each flow had open (R1.6.2), the balance the
    next reading starts from and the comparison of the balance it made (R3.3.1).

    A reading saved before the balances were compared has no reference: the next one takes it from the exchange.
    """

    account_id: UUID
    read_at: datetime
    open_assets: Mapping[FlowId, frozenset[str]]
    reference_balance: Decimal | None = None
    comparison: BalanceComparison | None = None

    def confirmed(self) -> AccountReading:
        """The user checked the account: the balance read becomes the reference of the next comparison (R3.3.1)."""
        if self.comparison is None:
            return self
        return replace(self, reference_balance=self.comparison.read)


@dataclass(frozen=True, slots=True)
class OutsideClosing:
    """A position of a flow gone from the exchange without an order of the flow, with the outcome read there and
    whether the exchange liquidated it.
    """

    flow_id: FlowId
    asset: str
    realized_pnl: Decimal
    fee: Decimal
    closed_at: datetime
    liquidation: bool = False

    @property
    def reason_told(self) -> CloseReason:
        """The reason the closing is told by: a liquidation is an event of its own (R3.5.1), while the history keeps
        every closing outside the platform, liquidations included, as such (R1.7.2).
        """
        return CloseReason.LIQUIDATION if self.liquidation else CloseReason.OUTSIDE_PLATFORM


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
    """What a reading of the account shows that no flow explains, compared with the previous reading (R1.6.2), and
    whether its balance is the one expected (R3.3.1).

    The executions are those the ledger has just recorded (ADR 0063). Without a previous reading, past executions and
    movements are the starting point, not something to report.
    The expected balance is the reference of the previous reading plus the executions, fees and funding of the flows
    and the deposits and withdrawals the exchange declares since then. A deviation within the threshold is a change of
    the balance no flow explains, and the balance read becomes the reference; beyond it, an alarm, and the expected
    balance stays the reference until the user confirms.
    """

    items: tuple[UnattributableItem, ...]
    closed_outside: tuple[OutsideClosing, ...]
    reading: AccountReading
    open_assets: frozenset[str]
    closed_by_protection: tuple[ProtectionClosing, ...] = ()
    comparison: BalanceComparison | None = None
    alarm: ReconciliationAlarm | None = None

    @classmethod
    def of(  # noqa: PLR0913, PLR0917 - the readings a reconciliation compares and the threshold it compares with
        cls,
        account_id: UUID,
        flows_of_account: Iterable[Flow],
        activity: AccountActivity,
        previous: AccountReading | None,
        recorded: AccountLedger,
        threshold_percent: Decimal,
    ) -> AccountReconciliation:
        flows = [flow for flow in flows_of_account if flow.status != FlowStatus.ARCHIVED]
        new_entries = () if previous is None else recorded.entries
        comparison = _comparison(previous, recorded, activity)
        alarm = _alarm(account_id, comparison, threshold_percent)
        reading = AccountReading(
            account_id,
            activity.read_at,
            _open_assets_of(flows, activity),
            _next_reference(comparison, alarm, activity),
            comparison,
        )
        return cls(
            items=(
                *_unowned_positions(account_id, flows, activity),
                *_unknown_fills(account_id, new_entries, activity.read_at),
                *_balance_change(account_id, comparison, alarm),
            ),
            closed_outside=() if previous is None else _closed_outside(previous, reading, new_entries, activity),
            reading=reading,
            open_assets=activity.open_assets,
            closed_by_protection=() if previous is None else _closed_by_protection(previous, reading, new_entries),
            comparison=comparison,
            alarm=alarm,
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


def _read_balance(activity: AccountActivity) -> Decimal:
    return activity.balance - sum((position.unrealized_pnl for position in activity.positions), ZERO)


def _comparison(
    previous: AccountReading | None, recorded: AccountLedger, activity: AccountActivity
) -> BalanceComparison | None:
    if previous is None or previous.reference_balance is None:
        return None
    expected = previous.reference_balance + _explained(recorded, activity, previous.read_at)
    return BalanceComparison(expected, _read_balance(activity), activity.read_at)


def _explained(recorded: AccountLedger, activity: AccountActivity, since: datetime) -> Decimal:
    """What moved the balance since the last reading with a reason: the flows, and what the exchange declares."""
    executions = sum(
        (entry.execution.realized_pnl - entry.execution.fee for entry in recorded.entries if entry.flow_id is not None),
        ZERO,
    )
    funding = sum((entry.payment.amount for entry in recorded.funding if entry.flow_id is not None), ZERO)
    movements = sum((movement.amount for movement in activity.movements if movement.moved_at > since), ZERO)
    return executions + funding + movements


def _alarm(
    account_id: UUID, comparison: BalanceComparison | None, threshold_percent: Decimal
) -> ReconciliationAlarm | None:
    if comparison is None or not comparison.exceeds(threshold_percent):
        return None
    return ReconciliationAlarm.of(account_id, comparison)


def _next_reference(
    comparison: BalanceComparison | None, alarm: ReconciliationAlarm | None, activity: AccountActivity
) -> Decimal:
    if comparison is None:
        return _read_balance(activity)
    # Beyond the threshold the deviation stays until the user confirms, so every next reading sees it again.
    return comparison.expected if alarm is not None else comparison.read


def _balance_change(
    account_id: UUID, comparison: BalanceComparison | None, alarm: ReconciliationAlarm | None
) -> list[UnattributableItem]:
    if comparison is None or alarm is not None or comparison.difference == ZERO:
        return []
    # Each comparison is a case of its own: the moment of the reading tells one from the next.
    return [
        UnattributableItem(
            account_id,
            UnattributableKind.BALANCE_CHANGE,
            comparison.compared_at.isoformat(),
            None,
            comparison.difference,
            comparison.compared_at,
        )
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
        liquidation=any(execution.liquidation for execution in outside),
    )
