from uuid import UUID


class FakeOrderRejectedNoticeAdapter:
    """Keeps the orders a use case tells refused, instead of sending them to the chat; a list shared with other fakes
    keeps the order of every notice."""

    def __init__(self, told: list[tuple[object, ...]] | None = None) -> None:
        self.told: list[tuple[object, ...]] = [] if told is None else told

    def execute(self, flow_id: UUID, flow_name: str, message: str) -> None:
        self.told.append(("rifiutato", flow_id, flow_name, message))
