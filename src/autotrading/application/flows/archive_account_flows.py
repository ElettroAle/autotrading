from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.archive_flow import ArchiveFlowCommand, ArchiveFlowUseCase
from autotrading.application.flows.ports import FlowRepositoryPort


@dataclass(frozen=True, slots=True)
class ArchiveAccountFlowsCommand:
    account_id: UUID


class ArchiveAccountFlowsUseCase:
    """Archives the stopped flows of an account that is being removed (R1.1.8)."""

    def __init__(self, flows: FlowRepositoryPort, archive: ArchiveFlowUseCase) -> None:
        self._flows = flows
        self._archive = archive

    def execute(self, command: ArchiveAccountFlowsCommand) -> None:
        for flow in self._flows.list():
            if flow.archivable_on(command.account_id):
                self._archive.execute(ArchiveFlowCommand(flow.id))
