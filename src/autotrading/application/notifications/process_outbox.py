from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.ports import OutboxPort


class ProcessOutboxUseCase:
    """Delivers the messages of the outbox for as long as the worker runs, each with the port of its integration
    (ADR outbox-delle-integrazioni-esterne-con-procrastinate).
    """

    def __init__(self, outbox: OutboxPort, deliver: DeliverOutboxMessageUseCase) -> None:
        self._outbox = outbox
        self._deliver = deliver

    def execute(self) -> None:
        self._outbox.process(self._deliver.execute)
