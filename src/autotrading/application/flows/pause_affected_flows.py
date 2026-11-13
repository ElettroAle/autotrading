from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import AutomaticPausePort, FlowRepositoryPort, PausedFlowNoticePort
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus


@dataclass(frozen=True, slots=True)
class PauseAffectedFlowsCommand:
    """A permanent error of a cycle, with the account or the provider it concerns when it concerns one (R1.2.4)."""

    flow_id: UUID
    reason: str
    account_id: UUID | None = None
    provider: str | None = None

    @classmethod
    def of_error(cls, flow_id: UUID, error: AutotradingError) -> PauseAffectedFlowsCommand:
        """The error declares what it concerns beyond the flow of its cycle; its message is the reason (ADR 0082)."""
        scope = error.scope
        return cls(flow_id, str(error), account_id=scope.account_id, provider=scope.provider)


class PauseAffectedFlowsUseCase:
    """Pauses the flow of the cycle and every other active flow the permanent error involves (R1.2.4).

    The credentials of an account involve every flow of the account; the key of a provider, every flow on a model
    of that provider. The positions stay open on the exchange: a pause sends no order.
    """

    def __init__(self, flows: FlowRepositoryPort, pause: AutomaticPausePort, notices: PausedFlowNoticePort) -> None:
        self._flows = flows
        self._pause = pause
        self._notices = notices

    def execute(self, command: PauseAffectedFlowsCommand) -> list[Flow]:
        affected = [flow for flow in self._flows.list() if _involved(flow, command)]
        self._pause.pause([flow.id for flow in affected], command.reason)
        for flow in affected:
            self._notices.paused(flow, command.reason)
        return affected


def _involved(flow: Flow, command: PauseAffectedFlowsCommand) -> bool:
    if flow.status is not FlowStatus.ACTIVE:
        return False
    return (
        flow.id.value == command.flow_id
        or flow.account_id == command.account_id
        or flow.model_provider == command.provider
    )
