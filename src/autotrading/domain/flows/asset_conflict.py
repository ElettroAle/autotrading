from collections.abc import Iterable
from uuid import UUID

from autotrading.domain.flows.errors import AssetsAssignedToOtherFlowError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus


def require_assets_free(
    account_id: UUID, assets: tuple[str, ...], flows: Iterable[Flow], excluding: FlowId | None = None
) -> None:
    """No other flow of the account, archived ones aside, already trades one of the assets (R1.1.2)."""
    for flow in flows:
        if flow.account_id != account_id or flow.status == FlowStatus.ARCHIVED or flow.id == excluding:
            continue
        shared = tuple(asset for asset in assets if asset in flow.configuration.assets)
        if shared:
            raise AssetsAssignedToOtherFlowError(flow.name.value, shared)
