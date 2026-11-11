"""Fake of the account of a flow as the flows context reads it: exchange and balance, or not found, or out of reach."""

from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.ports import FlowAccount


class FakeFlowAccountAdapter:
    def __init__(self) -> None:
        self.accounts: dict[UUID, FlowAccount] = {}
        self.reachable = True

    def add(self, account_id: UUID, balance: Decimal, exchange: str = "Hyperliquid") -> None:
        self.accounts[account_id] = FlowAccount(exchange, balance, "USDC")

    def account(self, account_id: UUID) -> FlowAccount:
        if account_id not in self.accounts:
            raise FlowAccountNotFoundError
        if not self.reachable:
            raise FlowExchangeUnavailableError
        return self.accounts[account_id]
