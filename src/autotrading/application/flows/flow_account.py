from uuid import UUID

from autotrading.application.flows.ports import FlowAccountPorts, FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.free_capital import FreeCapital
from autotrading.domain.flows.ledger import FlowTotals


def read_free_capital(
    flows: FlowRepositoryPort, accounts: FlowAccountPorts, account_id: UUID, excluding: FlowId | None = None
) -> FreeCapital:
    """The free capital of the account read now: its balance less the total value of every flow holding it, but the
    one left out (ADR capitale-libero-al-netto-del-valore-dei-flussi, ADR 0142).

    One reading of the account gives balance and positions, so every flow is valued on the same instant; its money
    comes from the totals of the ledger, net of the profits it cashed out.
    """
    activity = accounts.activity.execute(account_id)
    holding = [
        flow
        for flow in flows.list()
        if flow.belongs_to(account_id) and flow.status.holds_account and flow.id != excluding
    ]
    flow_ids = [flow.id for flow in holding]
    totals = accounts.ledger.totals_of(flow_ids)
    changes = flows.capital_changes_of(flow_ids)
    states = [
        FlowState.attributed(flow, activity, totals.get(flow.id) or FlowTotals(flow.id), changes.get(flow.id, ()))
        for flow in holding
    ]
    return FreeCapital.of(activity.balance, activity.currency, states)
