"""Fake of the account of a flow as the flows context reads it: the exchange from the accounts of the tenant, the
balance and the positions from what the exchange shows, the totals of the flows from the ledger (ADR
capitale-libero-al-netto-del-valore-dei-flussi)."""

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.ports import FlowAccountPorts
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.support.activity import an_activity


class FakeFlowAccountAdapter:
    def __init__(
        self, activity: FakeAccountActivityAdapter | None = None, ledger: InMemoryFlowLedgerAdapter | None = None
    ) -> None:
        self.exchanges: dict[UUID, str] = {}
        self.activity = FakeAccountActivityAdapter() if activity is None else activity
        self.ledger = InMemoryFlowLedgerAdapter() if ledger is None else ledger

    @property
    def reachable(self) -> bool:
        return self.activity.reachable

    @reachable.setter
    def reachable(self, reachable: bool) -> None:
        self.activity.reachable = reachable

    def add(self, account_id: UUID, balance: Decimal, exchange: str = "Hyperliquid") -> None:
        self.exchanges[account_id] = exchange
        self.set_balance(account_id, balance)

    def set_balance(self, account_id: UUID, balance: Decimal) -> None:
        """The balance the exchange shows now, the positions on the account kept."""
        reading = self.activity.activities.get(account_id, an_activity())
        self.activity.activities[account_id] = replace(reading, balance=balance, available_margin=balance)

    def ports(self) -> FlowAccountPorts:
        return FlowAccountPorts(self, self.activity, self.ledger)

    def exchange_of(self, account_id: UUID) -> str:
        if account_id not in self.exchanges:
            raise FlowAccountNotFoundError
        return self.exchanges[account_id]
