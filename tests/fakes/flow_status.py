from autotrading.application.notifications.errors import FlowStatusUnavailableError
from autotrading.domain.notifications.flow_status import FlowStatusFigures


class FakeFlowStatusAdapter:
    """The state of the flows as their last cycles recorded it, by name; or a store that cannot be read."""

    def __init__(self) -> None:
        self.readable = True
        self.figures: dict[str, FlowStatusFigures] = {}
        self.asked: list[str] = []

    def status_of(self, flow_name: str) -> FlowStatusFigures | None:
        self.asked.append(flow_name)
        if not self.readable:
            raise FlowStatusUnavailableError
        return self.figures.get(flow_name)
