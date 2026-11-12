"""In-memory ledger of the executions with the running totals of the flows, as the SQL adapter keeps them."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import AccountLedger, FlowTotals, FundingEntry, LedgerEntry, LedgerKeys


@dataclass
class InMemoryFlowLedgerAdapter:
    entries: dict[UUID, list[LedgerEntry]] = field(default_factory=dict)
    funding: dict[UUID, list[FundingEntry]] = field(default_factory=dict)
    cursors: dict[UUID, datetime] = field(default_factory=dict)
    totals: dict[FlowId, FlowTotals] = field(default_factory=dict)

    def cursor(self, account_id: UUID) -> datetime | None:
        return self.cursors.get(account_id)

    def recorded_since(self, account_id: UUID, since: datetime) -> LedgerKeys:
        return LedgerKeys(
            frozenset(
                entry.execution.key
                for entry in self.entries.get(account_id, [])
                if entry.execution.executed_at >= since
            ),
            frozenset(
                entry.payment.key for entry in self.funding.get(account_id, []) if entry.payment.paid_at >= since
            ),
        )

    def record(self, account_id: UUID, ledger: AccountLedger, cursor: datetime) -> tuple[LedgerEntry, ...]:
        recorded = self.entries.setdefault(account_id, [])
        known = {entry.execution.key for entry in recorded}
        added = tuple(entry for entry in ledger.entries if entry.execution.key not in known)
        recorded.extend(added)
        for entry in added:
            if entry.flow_id is not None:
                self.totals[entry.flow_id] = self._of(entry.flow_id).with_execution(entry.execution)
        payments = self.funding.setdefault(account_id, [])
        paid = {entry.payment.key for entry in payments}
        for payment in (entry for entry in ledger.funding if entry.payment.key not in paid):
            payments.append(payment)
            if payment.flow_id is not None:
                self.totals[payment.flow_id] = self._of(payment.flow_id).with_funding(payment.payment)
        self.cursors[account_id] = max(cursor, self.cursors.get(account_id, cursor))
        return added

    def totals_of(self, flow_ids: Iterable[FlowId]) -> Mapping[FlowId, FlowTotals]:
        return {flow_id: self.totals[flow_id] for flow_id in flow_ids if flow_id in self.totals}

    def entries_of(self, flow_id: FlowId) -> list[LedgerEntry]:
        return [entry for entries in self.entries.values() for entry in entries if entry.flow_id == flow_id]

    def recomputed(self, flow_id: FlowId) -> FlowTotals:
        totals = FlowTotals(flow_id)
        for entry in self.entries_of(flow_id):
            totals = totals.with_execution(entry.execution)
        for payments in self.funding.values():
            for payment in payments:
                if payment.flow_id == flow_id:
                    totals = totals.with_funding(payment.payment)
        return totals

    def realized(self, flow_id: FlowId) -> Decimal:
        return self._of(flow_id).realized_pnl

    def _of(self, flow_id: FlowId) -> FlowTotals:
        return self.totals.get(flow_id) or FlowTotals(flow_id)
