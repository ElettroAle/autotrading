from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.ports import PastDecisionsPort
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.memory_entry import AssetMemory


def remembered_decisions(
    decisions: PastDecisionsPort,
    flow_id: UUID,
    configuration: FlowConfiguration,
    at: datetime,
    unrealized_pnl: Mapping[str, Decimal],
) -> tuple[AssetMemory, ...] | None:
    """What the agent of the flow remembers at the instant given, for every asset of the configuration; None when the
    memory of the flow is off, without reading anything (R5.3.4).

    The cycle and the consultation of the flow read it alike: what the page shows is what the next cycle receives.
    """
    memory = configuration.memory
    if not memory.active:
        return None
    past = decisions.past_decisions(flow_id, memory.window(at))
    return memory.recalled(configuration.assets, past, at, unrealized_pnl)
