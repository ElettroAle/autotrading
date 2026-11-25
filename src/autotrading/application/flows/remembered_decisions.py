from collections.abc import Callable, Iterable
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import PastDecisionsPort
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.cycle_account import CyclePosition
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.memory_entry import AssetMemory

type OpenPosition = CyclePosition | AccountPosition


def remembered_decisions(
    decisions: PastDecisionsPort,
    flow_id: UUID,
    configuration: FlowConfiguration,
    at: datetime,
    open_positions: Callable[[], Iterable[OpenPosition]],
) -> tuple[AssetMemory, ...] | None:
    """What the agent of the flow remembers at the instant given, for every asset of the configuration; None when the
    memory of the flow is off, without reading anything (R5.3.4).

    The cycle and the consultation of the flow read it alike: what the page shows is what the next cycle receives. The
    positions of the account are asked for only with the memory on; those of the flow give their unrealized PnL.
    """
    memory = configuration.memory
    if not memory.active:
        return None
    past = decisions.past_decisions(flow_id, memory.window(at), memory.remembered_actions)
    held = configuration.held(open_positions(), lambda position: position.asset)
    unrealized_pnl = {position.asset: position.unrealized_pnl for position in held}
    return memory.recalled(configuration.assets, past, at, unrealized_pnl)
