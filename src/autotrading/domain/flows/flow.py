from dataclasses import dataclass
from uuid import UUID

from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

FIRST_VERSION = 1


@dataclass(frozen=True, slots=True)
class Flow(TenantOwned):
    """An agent trading on one account of the tenant, with the configuration version in force (R1.1.1)."""

    id: FlowId
    tenant_id: TenantId
    account_id: UUID
    name: FlowName
    status: FlowStatus
    configuration: FlowConfiguration

    @classmethod
    def created(cls, tenant_id: TenantId, account_id: UUID, name: FlowName, configuration: FlowConfiguration) -> Flow:
        """A new flow is stopped: it runs no cycle until the user starts it."""
        return cls(FlowId.new(), tenant_id, account_id, name, FlowStatus.STOPPED, configuration)

    @property
    def model_provider(self) -> str:
        return self.configuration.model.name.partition("/")[0]
