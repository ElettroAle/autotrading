from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel

from autotrading.application.flows.create_flow import MemoryRequest
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome


class FlowMemoryBody(BaseModel):
    """The memory of a flow as the user sets it: a part left out keeps the one in force, or the default (R5.3.4)."""

    active: bool | None = None
    decisions: int | None = None
    days: int | None = None

    def request(self) -> MemoryRequest:
        return MemoryRequest(active=self.active, decisions=self.decisions, days=self.days)


class FlowMemorySettingsResponse(BaseModel):
    active: bool
    decisions: int
    days: int

    @classmethod
    def of(cls, memory: FlowMemory) -> FlowMemorySettingsResponse:
        return cls(active=memory.active, decisions=memory.decisions, days=memory.days)


class MemoryOutcomeResponse(BaseModel):
    # Numbers travel as strings, so no precision is lost on the way (ADR 0018).
    pnl: str
    realized: bool

    @classmethod
    def of(cls, outcome: MemoryOutcome | None) -> MemoryOutcomeResponse | None:
        if outcome is None:
            return None
        return cls(pnl=str(outcome.pnl), realized=outcome.realized)


class MemoryEntryResponse(BaseModel):
    """A previous operative decision of the flow: no price without an execution, no outcome without a position."""

    planned_at: datetime
    action: str
    direction: str | None
    price: str | None
    reasoning: str
    outcome: MemoryOutcomeResponse | None

    @classmethod
    def of(cls, entry: MemoryEntry) -> MemoryEntryResponse:
        return cls(
            planned_at=entry.planned_at,
            action=entry.action.value,
            direction=None if entry.direction is None else entry.direction.value,
            price=None if entry.price is None else str(entry.price),
            reasoning=entry.reasoning,
            outcome=MemoryOutcomeResponse.of(entry.outcome),
        )


class AssetMemoryResponse(BaseModel):
    asset: str
    decisions: list[MemoryEntryResponse]

    @classmethod
    def all_of(cls, memory: Sequence[AssetMemory]) -> list[AssetMemoryResponse]:
        return [
            cls(asset=asset.asset, decisions=[MemoryEntryResponse.of(entry) for entry in asset.entries])
            for asset in memory
        ]


class FlowMemoryResponse(BaseModel):
    """What the agent of the flow would receive if its cycle started now; nothing when its memory is off (R5.3.4)."""

    active: bool
    assets: list[AssetMemoryResponse]

    @classmethod
    def of(cls, memory: Sequence[AssetMemory] | None) -> FlowMemoryResponse:
        if memory is None:
            return cls(active=False, assets=[])
        return cls(active=True, assets=AssetMemoryResponse.all_of(memory))
