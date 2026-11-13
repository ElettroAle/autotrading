"""Fake of the account of a flow as the flows context reads it: exchange and balance, or not found, or out of reach."""

from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.ports import FlowAccountPorts, FlowBalance


class FakeFlowAccountAdapter:
    def __init__(self) -> None:
        self.exchanges: dict[UUID, str] = {}
        self.balances: dict[UUID, Decimal] = {}
        self.reachable = True

    def add(self, account_id: UUID, balance: Decimal, exchange: str = "Hyperliquid") -> None:
        self.exchanges[account_id] = exchange
        self.balances[account_id] = balance

    def ports(self) -> FlowAccountPorts:
        return FlowAccountPorts(self, self)

    def exchange_of(self, account_id: UUID) -> str:
        if account_id not in self.exchanges:
            raise FlowAccountNotFoundError
        return self.exchanges[account_id]

    def balance_of(self, account_id: UUID) -> FlowBalance:
        if account_id not in self.balances:
            raise FlowAccountNotFoundError
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return FlowBalance(self.balances[account_id], "USDC")
