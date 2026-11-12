"""The cycles of the flows as the user consults them: the cycle runner and the platform on the same records."""

from dataclasses import replace
from uuid import UUID

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.domain.cycles.cycle_record import CycleRecord
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.cycles import Cycles
from tests.support.flows import OPENROUTER_MODEL, a_configuration, a_flow
from tests.support.platform import Platform


class Records:
    def __init__(self) -> None:
        self.platform = Platform()
        self.cycles = Cycles()
        # The runner records the cycles where the platform reads them, as the database does for worker and API.
        self.platform.cycles = self.cycles.records
        self.consulted: object = None

    def add_flow(self, user: str, name: str, version: int = 1, model: str = OPENROUTER_MODEL) -> UUID:
        configuration = replace(a_configuration(model=model), version=version)
        flow = a_flow(self.platform.tenant_of(user), name=name, status=FlowStatus.ACTIVE, configuration=configuration)
        self.platform.flows.flows.append(flow)
        self.cycles.add_flow(name, flow_id=flow.id.value)
        return flow.id.value

    def add_records(self, *records: CycleRecord) -> None:
        for record in records:
            self.cycles.records.record(record)

    def use_cases_of(self, user: str) -> TenantUseCases:
        return self.platform.use_cases_of(user)

    def release(self) -> None:
        self.cycles.release()
