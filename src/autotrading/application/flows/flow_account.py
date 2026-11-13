from uuid import UUID

from autotrading.application.flows.ports import FlowAccount, FlowAccountPorts


def read_flow_account(ports: FlowAccountPorts, account_id: UUID) -> FlowAccount:
    """The exchange of the account first: one the tenant does not have is not found before its balance is read."""
    exchange = ports.directory.exchange_of(account_id)
    balance = ports.balances.balance_of(account_id)
    return FlowAccount(exchange, balance.amount, balance.currency)
