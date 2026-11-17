import logging
from dataclasses import dataclass

from autotrading.application.flows.errors import FlowNameInUseError
from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class DuplicateFlowCommand:
    flow_id: FlowId


class DuplicateFlowUseCase:
    """Saves a draft with the strategy of a flow of the tenant, to try a variant of it (R2.4.1, ADR 0124).

    The copy has its own history from version 1, the account and the capital of the original and no assets: the user
    chooses them in its configuration before starting it (ADR bozza-configurata-dall-editor-e-duplica-con-conto). The
    free capital is not read: a draft takes nothing on its account until it starts. Cycles and positions of the
    original stay where they are.
    """

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: DuplicateFlowCommand) -> Flow:
        copy = self._flows.get(command.flow_id).duplicated()
        self._require_free_name(copy)
        self._flows.add(copy)
        operations.info("flusso duplicato", extra={"flow_id": str(copy.id.value)})
        return copy

    def _require_free_name(self, copy: Flow) -> None:
        if self._flows.name_in_use(copy.name):
            raise FlowNameInUseError
