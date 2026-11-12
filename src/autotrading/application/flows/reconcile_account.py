from dataclasses import dataclass

from autotrading.application.flows.ports import (
    AccountActivityPort,
    ClosedPositionsPort,
    FlowRepositoryPort,
    PlatformOrdersPort,
    ReconciliationRepositoryPort,
)
from autotrading.application.flows.read_flow_state import find_flow
from autotrading.domain.flows.account_reconciliation import AccountReconciliation, OutsideClosing
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.unattributable import UnattributableItem


@dataclass(frozen=True, slots=True)
class ReconcileAccountCommand:
    flow_id: FlowId


@dataclass(frozen=True, slots=True)
class ReconciliationOutcome:
    """What this reconciliation found for the first time, for the notifications of the cycle (R1.8.2)."""

    new_items: tuple[UnattributableItem, ...]
    closed_outside: tuple[OutsideClosing, ...]


class ReconcileAccountUseCase:
    """At every cycle of a flow, what the account of the flow shows that no flow explains (R1.6.2).

    Every case is recorded once; a position of a flow closed outside the platform enters the history of the flow.
    Nothing on the exchange is touched, and the flows keep operating.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        activity: AccountActivityPort,
        orders: PlatformOrdersPort,
        readings: ReconciliationRepositoryPort,
        closed_positions: ClosedPositionsPort,
    ) -> None:
        self._flows = flows
        self._activity = activity
        self._orders = orders
        self._readings = readings
        self._closed_positions = closed_positions

    def execute(self, command: ReconcileAccountCommand) -> ReconciliationOutcome:
        account_id = find_flow(self._flows, command.flow_id).account_id
        reconciliation = AccountReconciliation.of(
            account_id,
            (flow for flow in self._flows.list() if flow.account_id == account_id),
            self._activity.activity(account_id),
            self._orders.orders_of_account(account_id),
            self._readings.last_reading(account_id),
        )
        new_items = tuple(item for item in reconciliation.items if self._readings.record(item))
        self._readings.resolve_positions(account_id, reconciliation.open_assets)
        for closing in reconciliation.closed_outside:
            self._closed_positions.add_closed_outside(closing)
        self._readings.save_reading(reconciliation.reading)
        return ReconciliationOutcome(new_items, reconciliation.closed_outside)
