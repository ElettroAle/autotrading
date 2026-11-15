from collections.abc import Callable
from enum import StrEnum

from autotrading.application.notifications.errors import OutboxUnavailableError
from autotrading.domain.errors import AutotradingError
from autotrading.domain.notifications.outbox_message import OutboxMessage
from autotrading.domain.notifications.outbox_message_id import OutboxMessageId

MAXIMUM_ATTEMPTS = 8


class OutboxState(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class InMemoryOutboxAdapter:
    """The outbox as the tests see it, with no time: once processing starts, a message is delivered as soon as it is
    queued, as the worker of the queue does; a transient failure waits for the test to let the backoff pass.
    """

    def __init__(self, maximum_attempts: int = MAXIMUM_ATTEMPTS) -> None:
        self.reachable = True
        self.messages: list[OutboxMessage] = []
        self.states: dict[OutboxMessageId, OutboxState] = {}
        self.attempts: dict[OutboxMessageId, int] = {}
        self._maximum_attempts = maximum_attempts
        self._deliver: Callable[[OutboxMessage], None] | None = None

    def enqueue(self, message: OutboxMessage) -> None:
        if not self.reachable:
            raise OutboxUnavailableError
        self.messages.append(message)
        self.states[message.id] = OutboxState.PENDING
        self.attempts[message.id] = 0
        self._attempt(message)

    def process(self, deliver: Callable[[OutboxMessage], None]) -> None:
        self._deliver = deliver
        self.let_backoff_pass()

    def let_backoff_pass(self) -> None:
        for message in self.in_state(OutboxState.PENDING):
            self._attempt(message)

    def in_state(self, state: OutboxState) -> list[OutboxMessage]:
        return [message for message in self.messages if self.states[message.id] is state]

    def _attempt(self, message: OutboxMessage) -> None:
        if self._deliver is None:
            return
        self.attempts[message.id] += 1
        try:
            self._deliver(message)
        except AutotradingError as error:
            last = error.permanent or self.attempts[message.id] >= self._maximum_attempts
            self.states[message.id] = OutboxState.FAILED if last else OutboxState.PENDING
            return
        self.states[message.id] = OutboxState.DELIVERED
