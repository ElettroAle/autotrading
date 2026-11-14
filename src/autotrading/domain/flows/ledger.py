from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PlatformOrder:
    """An order the platform sent on the account: the flow that sent it, if any, and whether the verification
    procedure sent it (R0.4.1)."""

    flow_id: FlowId | None
    verification: bool = False


type PlatformOrders = Mapping[UUID, PlatformOrder]


class ExecutionKind(StrEnum):
    """Why an execution of the account belongs to a flow, or to none (ADR 0063)."""

    FLOW_ORDER = "ordine_flusso"
    LIQUIDATION = "liquidazione"
    OUTSIDE_CLOSING = "chiusura_fuori"
    UNATTRIBUTED = "non_attribuita"


@dataclass(frozen=True, slots=True)
class Execution:
    """One execution of the account as the exchange reports it; sizes are signed, positive for a purchase."""

    fill_id: str
    exchange_order_id: str
    order_id: UUID | None
    asset: str
    size: Decimal
    price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    start_position: Decimal
    liquidation: bool
    executed_at: datetime

    @property
    def key(self) -> tuple[str, str]:
        return self.fill_id, self.exchange_order_id


@dataclass(frozen=True, slots=True)
class FundingPayment:
    """A funding payment of an open position: positive when the account receives it."""

    asset: str
    amount: Decimal
    paid_at: datetime

    @property
    def key(self) -> tuple[str, datetime]:
        return self.asset, self.paid_at


@dataclass(frozen=True, slots=True)
class ExecutionsWindow:
    """What the exchange still holds of an account since a moment; incomplete when part of it is gone already."""

    executions: tuple[Execution, ...]
    funding: tuple[FundingPayment, ...]
    complete: bool

    @property
    def order_ids(self) -> frozenset[UUID]:
        return frozenset(execution.order_id for execution in self.executions if execution.order_id is not None)


@dataclass(frozen=True, slots=True)
class LedgerKeys:
    """What of an account the ledger holds already: executions by fill and order, funding by asset and moment."""

    executions: frozenset[tuple[str, str]] = frozenset()
    funding: frozenset[tuple[str, datetime]] = frozenset()

    def unknown_in(self, window: ExecutionsWindow) -> ExecutionsWindow:
        return replace(
            window,
            executions=tuple(execution for execution in window.executions if execution.key not in self.executions),
            funding=tuple(payment for payment in window.funding if payment.key not in self.funding),
        )


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    execution: Execution
    flow_id: FlowId | None
    kind: ExecutionKind
    platform_order: bool = False


@dataclass(frozen=True, slots=True)
class FundingEntry:
    payment: FundingPayment
    flow_id: FlowId | None


@dataclass(frozen=True, slots=True)
class FlowTotals:
    """The running totals of a flow kept with its ledger: what the cycle reads instead of the executions (ADR 0063)."""

    flow_id: FlowId
    realized_pnl: Decimal = ZERO
    fees: Decimal = ZERO
    funding: Decimal = ZERO
    positions: Mapping[str, Decimal] = field(default_factory=lambda: frozendict({}))

    def expected(self, asset: str) -> Decimal:
        return self.positions.get(asset, ZERO)

    def with_execution(self, execution: Execution) -> FlowTotals:
        positions = {**self.positions, execution.asset: self.expected(execution.asset) + execution.size}
        return replace(
            self,
            realized_pnl=self.realized_pnl + execution.realized_pnl,
            fees=self.fees + execution.fee,
            positions=frozendict(positions),
        )

    def with_funding(self, payment: FundingPayment) -> FlowTotals:
        return replace(self, funding=self.funding + payment.amount)


@dataclass(frozen=True, slots=True)
class AccountLedger:
    """The new executions and funding of an account, each given to the flow it belongs to (ADR 0063).

    An order of the platform belongs to its flow; one sent for no flow (a manual command, a stop) belongs to the flow
    that owns the asset. Without an order of the platform, a liquidation and a closing of exactly the position the
    flow expects belong to that flow; anything else belongs to no flow.
    """

    entries: tuple[LedgerEntry, ...]
    funding: tuple[FundingEntry, ...]

    @property
    def latest(self) -> datetime | None:
        instants = [entry.execution.executed_at for entry in self.entries]
        instants += [entry.payment.paid_at for entry in self.funding]
        return max(instants, default=None)

    @classmethod
    def attributed(
        cls,
        flows_of_account: Iterable[Flow],
        window: ExecutionsWindow,
        orders: PlatformOrders,
        totals: Mapping[FlowId, FlowTotals],
    ) -> AccountLedger:
        owners = _owners_of(flows_of_account)
        running = dict(totals)
        entries: list[LedgerEntry] = []
        funding: list[FundingEntry] = []
        events: list[Execution | FundingPayment] = [*window.executions, *window.funding]
        for event in sorted(events, key=_instant_of):
            if isinstance(event, Execution):
                entry = _entry_of(event, owners, orders, running)
                entries.append(entry)
                if entry.flow_id is not None:
                    running[entry.flow_id] = _totals(running, entry.flow_id).with_execution(event)
                continue
            holder = _holder_of(event, owners, running)
            funding.append(FundingEntry(event, holder))
            if holder is not None:
                running[holder] = _totals(running, holder).with_funding(event)
        return cls(tuple(entries), tuple(funding))


def _owners_of(flows: Iterable[Flow]) -> dict[str, FlowId]:
    # The conflict rule gives every asset of an account at most one flow in use (R1.1.2).
    return {asset: flow.id for flow in flows if flow.status.holds_account for asset in flow.configuration.assets}


def _instant_of(event: Execution | FundingPayment) -> datetime:
    return event.executed_at if isinstance(event, Execution) else event.paid_at


def _entry_of(
    execution: Execution,
    owners: Mapping[str, FlowId],
    orders: PlatformOrders,
    running: Mapping[FlowId, FlowTotals],
) -> LedgerEntry:
    owner = owners.get(execution.asset)
    if execution.order_id is not None and execution.order_id in orders:
        sent = orders[execution.order_id]
        if sent.verification:
            # The verification procedure runs on its own, whatever flow trades the asset (Bug 165, ADR 0075).
            return LedgerEntry(execution, None, ExecutionKind.UNATTRIBUTED, platform_order=True)
        flow_id = sent.flow_id or owner
        kind = ExecutionKind.FLOW_ORDER if flow_id is not None else ExecutionKind.UNATTRIBUTED
        return LedgerEntry(execution, flow_id, kind, platform_order=True)
    if owner is None:
        return LedgerEntry(execution, None, ExecutionKind.UNATTRIBUTED)
    if execution.liquidation:
        return LedgerEntry(execution, owner, ExecutionKind.LIQUIDATION)
    if _closes_exactly(execution, _totals(running, owner).expected(execution.asset)):
        return LedgerEntry(execution, owner, ExecutionKind.OUTSIDE_CLOSING)
    return LedgerEntry(execution, None, ExecutionKind.UNATTRIBUTED)


def _closes_exactly(execution: Execution, expected: Decimal) -> bool:
    return expected != ZERO and execution.start_position == expected and expected + execution.size == ZERO


def _totals(running: Mapping[FlowId, FlowTotals], flow_id: FlowId) -> FlowTotals:
    return running.get(flow_id) or FlowTotals(flow_id)


def _holder_of(
    payment: FundingPayment, owners: Mapping[str, FlowId], running: Mapping[FlowId, FlowTotals]
) -> FlowId | None:
    """Funding goes to the flow holding a position on the asset when it is paid; a position of no flow keeps it."""
    owner = owners.get(payment.asset)
    if owner is None or _totals(running, owner).expected(payment.asset) == ZERO:
        return None
    return owner
