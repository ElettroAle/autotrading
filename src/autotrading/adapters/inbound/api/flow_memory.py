from pydantic import BaseModel

from autotrading.domain.flows.memory_entry import AssetMemory


class FlowMemoryResponse(BaseModel):
    """What the agent of the flow would receive if its cycle started now; nothing when its memory is off (R5.3.4).

    The entries travel as the domain gives them, as in the cycle detail and in the tools of the flows: amounts as
    strings (ADR 0018), instants in ISO 8601, actions and directions as their values.
    """

    active: bool
    assets: tuple[AssetMemory, ...]

    @classmethod
    def of(cls, memory: tuple[AssetMemory, ...] | None) -> FlowMemoryResponse:
        if memory is None:
            return cls(active=False, assets=())
        return cls(active=True, assets=memory)
