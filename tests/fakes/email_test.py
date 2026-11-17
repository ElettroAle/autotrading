from collections.abc import Callable

from autotrading.application.notifications.errors import EmailNotDeliveredError


class FakeEmailTestAdapter:
    """The worker reached in process instead of over HTTP: the test email it sends now, for the same tenant."""

    def __init__(self, worker: Callable[[], None]) -> None:
        self._worker = worker
        self.reachable = True
        self.asked = 0

    def send_test(self) -> None:
        self.asked += 1
        if not self.reachable:
            raise EmailNotDeliveredError
        self._worker()
