from dataclasses import dataclass

from autotrading.application.flows.ports import FlowAccountNamePort, FlowRepositoryPort
from autotrading.domain.flows.emergency_closing import EmergencyScope
from autotrading.domain.flows.flow import Flow


@dataclass(frozen=True, slots=True)
class ListEmergencyFlowsCommand:
    scope: EmergencyScope


class ListEmergencyFlowsUseCase:
    """The flows an emergency closing covers, for the closing and for its confirmation alike (R3.2.3).

    A flow or an account the tenant lacks is refused as not found, the same answer as for one of another tenant
    (R0.1.3); an account without flows has none to close.
    """

    def __init__(self, flows: FlowRepositoryPort, accounts: FlowAccountNamePort) -> None:
        self._flows = flows
        self._accounts = accounts

    def execute(self, command: ListEmergencyFlowsCommand) -> tuple[Flow, ...]:
        scope = command.scope
        if scope.flow_id is not None:
            self._flows.get(scope.flow_id)
        if scope.account_id is not None:
            self._accounts.account_name(scope.account_id)
        return scope.flows_among(self._flows.list())
