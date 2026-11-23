from decimal import Decimal
from uuid import UUID


class FakePositionOpenedNoticeAdapter:
    """Keeps the openings a use case tells, instead of sending them to the chat; a list shared with other fakes keeps
    the order of every notice."""

    def __init__(self, told: list[tuple[object, ...]] | None = None) -> None:
        self.told: list[tuple[object, ...]] = [] if told is None else told

    def execute(  # noqa: PLR0917 - the signature of the port
        self, flow_id: UUID, flow_name: str, asset: str, direction: str, leverage: int, value: Decimal
    ) -> None:
        self.told.append(("aperta", flow_id, flow_name, asset, direction, leverage, value))
