from dataclasses import dataclass

from autotrading.application.flows.list_emergency_flows import ListEmergencyFlowsCommand, ListEmergencyFlowsUseCase
from autotrading.application.flows.ports import AccountActivityPort
from autotrading.domain.flows.emergency_closing import EmergencyClosingPreview, EmergencyScope


@dataclass(frozen=True, slots=True)
class PreviewEmergencyClosingCommand:
    scope: EmergencyScope


class PreviewEmergencyClosingUseCase:
    """What an emergency closing would touch now: its flows and the positions they hold, as the exchange shows them
    (R3.2.3, ADR chiusura-di-emergenza-nella-dashboard). It closes nothing; each account is read once.
    """

    def __init__(self, flows: ListEmergencyFlowsUseCase, activity: AccountActivityPort) -> None:
        self._flows = flows
        self._activity = activity

    def execute(self, command: PreviewEmergencyClosingCommand) -> EmergencyClosingPreview:
        flows = self._flows.execute(ListEmergencyFlowsCommand(command.scope))
        accounts = dict.fromkeys(flow.assigned_account_id for flow in flows)
        activities = {account_id: self._activity.execute(account_id) for account_id in accounts}
        return EmergencyClosingPreview.of(flows, activities)
