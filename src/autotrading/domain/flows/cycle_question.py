from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from autotrading.domain.flows.flow_state_view import FlowStateView
from autotrading.domain.flows.memory_entry import AssetMemory
from autotrading.domain.flows.selections import ModelParameterValue
from autotrading.domain.flows.source_data import SourceData


@dataclass(frozen=True, slots=True)
class CycleQuestion:
    """What a cycle asks the agent: the model of the flow, its system prompt rendered with the values of the flow
    (R1.4.8), its state and the data of its sources, and nothing else (R1.4.3).

    The memory the system prompt holds travels beside it, so the cycle records what the agent received (R5.3.4).
    """

    model: str
    settings: Mapping[str, ModelParameterValue]
    system_prompt: str
    assets: tuple[str, ...]
    started_at: datetime
    now: datetime
    state: FlowStateView
    sources: tuple[SourceData, ...]
    missing: tuple[str, ...]
    # None with the memory of the flow off: its placeholder in the system prompt is an empty text (R5.3.4).
    memory: tuple[AssetMemory, ...] | None = None
