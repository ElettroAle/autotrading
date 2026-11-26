from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import ClosedPositionRepositoryPort, PastDecisionsPort
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.memory_entry import AssetMemory
from autotrading.domain.flows.memory_summary import MemorySummary

# The account as the cycle reads it at its start, or as the exchange shows it now to the consultation.
type OpenAccount = CycleAccount | AccountActivity
type OpenPosition = CyclePosition | AccountPosition


@dataclass(frozen=True, slots=True)
class MemoryReadings:
    """What the memory of a flow reads: its past decisions and, for the summary, its closed positions (R5.3.4,
    R5.3.7).
    """

    decisions: PastDecisionsPort
    closings: ClosedPositionRepositoryPort


def remembered_decisions(
    readings: MemoryReadings,
    flow_id: UUID,
    configuration: FlowConfiguration,
    at: datetime,
    account: Callable[[], OpenAccount | None],
) -> tuple[AssetMemory, ...] | None:
    """What the agent of the flow remembers at the instant given, for every asset of the configuration; None when the
    memory of the flow is off, without reading anything (R5.3.4).

    The cycle and the consultation of the flow read it alike: what the page shows is what the next cycle receives. The
    account is asked for only with the memory on, None for a draft without one; the positions of the flow give their
    unrealized PnL, its currency that of the summary, whose closed positions are read only with an option of the
    summary on (R5.3.7, ADR memoria-del-flusso-con-riepilogo-e-altri-asset).
    """
    memory = configuration.memory
    if not memory.active:
        return None
    past = readings.decisions.past_decisions(flow_id, memory.window(at), memory.remembered_actions)
    read = account()
    held = configuration.held(_positions_of(read), lambda position: position.asset)
    unrealized_pnl = {position.asset: position.unrealized_pnl for position in held}
    summary = _summary(readings.closings, FlowId(flow_id), memory, at, read)
    return memory.recalled(configuration.assets, past, at, unrealized_pnl, summary)


def _positions_of(account: OpenAccount | None) -> tuple[OpenPosition, ...]:
    if account is None:
        return ()
    return account.positions


def _summary(
    closings: ClosedPositionRepositoryPort,
    flow_id: FlowId,
    memory: FlowMemory,
    at: datetime,
    account: OpenAccount | None,
) -> MemorySummary | None:
    """A flow without an account closed no position."""
    if not memory.summarizes or account is None:
        return None
    closed = closings.closed_within(flow_id, memory.window(at))
    return memory.summary_of(closed, at, account.currency)
