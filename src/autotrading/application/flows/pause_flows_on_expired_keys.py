from dataclasses import dataclass
from datetime import UTC
from uuid import UUID

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.ports import ClockPort, FlowKeysPort, FlowPausePort, FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_key import FlowKey


@dataclass(frozen=True, slots=True)
class PauseFlowsOnExpiredKeysCommand:
    """The flow whose cycle is due, or none for every flow of the tenant (the daily check)."""

    flow_id: UUID | None = None


class PauseFlowsOnExpiredKeysUseCase:
    """Pauses the active flows that use an expired key, with the reason «chiave <nome> scaduta», as for a key the
    provider revoked (R1.2.4, R6.2.2, ADR controllo-giornaliero-delle-scadenze): the existing pause, with its notice.

    The cycle asks it first for its own flow, which then does not start; the daily check, for every flow.
    """

    def __init__(self, keys: FlowKeysPort, flows: FlowRepositoryPort, pause: FlowPausePort, clock: ClockPort) -> None:
        self._keys = keys
        self._flows = flows
        self._pause = pause
        self._clock = clock

    def execute(self, command: PauseFlowsOnExpiredKeysCommand) -> bool:
        flows = self._flows_of(command)
        expired = self._expired_keys_used_by(flows)
        for key in expired:
            self._pause.execute(
                PauseAffectedFlowsCommand(command.flow_id, key.pause_reason, key.account_id, key.provider)
            )
        return bool(expired)

    def _flows_of(self, command: PauseFlowsOnExpiredKeysCommand) -> list[Flow]:
        if command.flow_id is None:
            return self._flows.list()
        return [self._flows.get(FlowId(command.flow_id))]

    def _expired_keys_used_by(self, flows: list[Flow]) -> list[FlowKey]:
        today = self._clock.now().astimezone(UTC).date()
        return [
            key
            for key in self._keys.dated_keys()
            if key.is_expired_on(today) and any(key.used_by(flow) for flow in flows)
        ]
