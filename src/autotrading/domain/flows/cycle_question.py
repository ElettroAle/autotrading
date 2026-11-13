from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from autotrading.domain.flows.flow_state_view import FlowStateView
from autotrading.domain.flows.selections import ModelParameterValue
from autotrading.domain.flows.source_data import SourceData


@dataclass(frozen=True, slots=True)
class CycleQuestion:
    """What a cycle asks the agent: the model of the flow, its instructions and limits, its state and the data of its
    sources, and nothing else (R1.4.3).
    """

    model: str
    settings: Mapping[str, ModelParameterValue]
    instructions: str
    assets: tuple[str, ...]
    max_leverage: int
    started_at: datetime
    now: datetime
    state: FlowStateView
    sources: tuple[SourceData, ...]
    missing: tuple[str, ...]
