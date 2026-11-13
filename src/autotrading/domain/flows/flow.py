from collections.abc import Iterable
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.errors import (
    ArchivedFlowNotModifiableError,
    ArchiveOnlyStoppedError,
    FlowCommandNotAllowedError,
)
from autotrading.domain.flows.flow_action import FlowAction
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

    def holds(self, account_id: UUID, asset: str) -> bool:
        """An active or paused flow keeps its asset on its account: nothing else may trade it there (ADR 0075).

        A stopped flow runs no cycle, so it leaves the asset free.
        """
        return self.account_id == account_id and self.status.not_stopped and self.configuration.covers(asset)

    def after(self, command: FlowAction) -> Flow:
        """The flow in the status the command leads to, when the command starts from its status (R1.1.4, R1.1.5)."""
        if self.status not in command.starts_from:
            raise FlowCommandNotAllowedError(command.value, self.status.value)
        return replace(self, status=command.leads_to)

    def archived(self) -> Flow:
        """Archiving is final, and only a stopped flow has no position left to manage (R1.1.6)."""
        if self.status != FlowStatus.STOPPED:
            raise ArchiveOnlyStoppedError
        return replace(self, status=FlowStatus.ARCHIVED)

    def require_modifiable(self) -> None:
        if self.status == FlowStatus.ARCHIVED:
            raise ArchivedFlowNotModifiableError

    def reconfigured(self, configuration: FlowConfiguration) -> Flow:
        """The flow with the configuration as its next version; the previous ones stay as they are (R1.1.3)."""
        self.require_modifiable()
        return replace(self, configuration=replace(configuration, version=self.configuration.version + 1))

    def with_capital(self, capital: Decimal) -> Flow:
        """The flow with another allocated capital as its next version: a cycle under way keeps its own (R1.1.7)."""
        return self.reconfigured(replace(self.configuration, allocated_capital=capital))


def holder_of(flows: Iterable[Flow], account_id: UUID, asset: str) -> str | None:
    """The name of the flow that holds the asset on the account, if one does (ADR 0075)."""
    holder = next((flow for flow in flows if flow.holds(account_id, asset)), None)
    if holder is None:
        return None
    return holder.name.value
