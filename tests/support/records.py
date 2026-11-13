"""The cycles of the flows as the user consults them: the cycle runner and the platform on the same records."""

from dataclasses import replace
from uuid import UUID

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.domain.flows.cycle_record import CycleRecord
from tests.support.cycles import Cycles
from tests.support.flow_cycles import FlowCycles
from tests.support.flows import OPENROUTER_MODEL


class Records:
    def __init__(self) -> None:
        # The flows live on the platform the bridges of the worker run on, so a cycle can also run for real.
        self.flow_cycles = FlowCycles()
        self.platform = self.flow_cycles.platform
        self.cycles = Cycles()
        self.flow_cycles.records = self.cycles.records
        # The runner records the cycles where the platform reads them, as the database does for worker and API.
        self.platform.cycles = self.cycles.records
        self.consulted: object = None

    def add_flow(self, user: str, name: str, version: int = 1, model: str = OPENROUTER_MODEL) -> UUID:
        flow = self.flow_cycles.add_flow(user, name, model=model)
        self.flow_cycles.reconfigure(name, lambda configuration: replace(configuration, version=version))
        self.cycles.add_flow(name, flow_id=flow.id.value)
        return flow.id.value

    def add_records(self, *records: CycleRecord) -> None:
        for record in records:
            self.cycles.records.record(record)

    def use_cases_of(self, user: str) -> TenantUseCases:
        return self.platform.use_cases_of(user)

    def release(self) -> None:
        self.cycles.release()
