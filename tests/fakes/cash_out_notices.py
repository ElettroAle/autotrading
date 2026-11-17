from decimal import Decimal
from uuid import UUID


class FakeCashOutNoticeAdapter:
    """Keeps the cash-outs a use case tells, instead of sending them to the chat of the tenant, and the flows they lead
    to (R3.5.6)."""

    def __init__(self) -> None:
        self.told: list[tuple[str, Decimal]] = []
        self.flows: list[UUID] = []

    def execute(self, flow_id: UUID, flow_name: str, freed: Decimal) -> None:
        self.told.append((flow_name, freed))
        self.flows.append(flow_id)
