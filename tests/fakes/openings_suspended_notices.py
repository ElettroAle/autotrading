from uuid import UUID


class FakeOpeningsSuspendedNoticeAdapter:
    """Keeps the suspensions of the openings a use case tells, instead of sending them to the chat; a list shared with
    other fakes keeps the order of every notice."""

    def __init__(self, told: list[tuple[object, ...]] | None = None) -> None:
        self.told: list[tuple[object, ...]] = [] if told is None else told

    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        self.told.append(("sospese", flow_id, flow_name, reason))
