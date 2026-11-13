"""A failed cycle told to the tenant of its flow, and to nobody else (R1.8.2, R0.1.3)."""

from uuid import UUID, uuid4

from autotrading.application.flows.tell_cycle_failure import TellCycleFailureUseCase
from autotrading.domain.tenancy.tenant_id import TenantId

ANNA, BRUNO = TenantId.new(), TenantId.new()


class Tenants:
    def __init__(self, tenants: dict[UUID, TenantId]) -> None:
        self._tenants = tenants

    def tenant_of(self, flow_id: UUID) -> TenantId:
        return self._tenants[flow_id]


class ToldFailures:
    def __init__(self) -> None:
        self.told: list[tuple[UUID, str]] = []

    def execute(self, flow_id: UUID, reason: str) -> None:
        self.told.append((flow_id, reason))


def test_the_failure_reaches_only_the_tenant_of_the_flow() -> None:
    flow = uuid4()
    told = {ANNA: ToldFailures(), BRUNO: ToldFailures()}

    TellCycleFailureUseCase(Tenants({flow: BRUNO}), told.__getitem__).execute(flow, "timeout")

    assert (told[ANNA].told, told[BRUNO].told) == ([], [(flow, "timeout")])
