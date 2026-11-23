from collections.abc import Callable

from autotrading.application.flows.ports import CycleWaitPort
from autotrading.domain.errors import AutotradingError

# Two more calls after the first, after 5 and then 15 seconds, as the owner asked ("Riprova sempre"): a system that is
# down a moment is up again within the cycle, one that stays down fails the cycle (ADR
# errori-temporanei-ritentati-in-ogni-passo-del-ciclo).
RETRY_PAUSES_SECONDS = (5.0, 15.0)

type FailedAttemptListener = Callable[[int, AutotradingError], None]


class TransientRetry:
    """The one policy of the cycle for a temporary error: the call is made again in the same cycle (ADR
    errori-temporanei-ritentati-in-ogni-passo-del-ciclo).

    An error the base error calls permanent comes out at once (R1.2.4); a temporary one is called again after each
    pause, and the last one comes out when no attempt went through. Every failed attempt is told, with its number, to
    whom the caller names: the record of the cycle shows them.
    """

    def __init__(self, wait: CycleWaitPort) -> None:
        self._wait = wait

    def run[T](self, call: Callable[[], T], failed: FailedAttemptListener) -> T:
        for attempt, pause in enumerate(RETRY_PAUSES_SECONDS, start=1):
            try:
                return call()
            except AutotradingError as error:
                failed(attempt, error)
                if error.permanent:
                    raise
            self._wait.pause(pause)
        try:
            return call()
        except AutotradingError as error:
            failed(len(RETRY_PAUSES_SECONDS) + 1, error)
            raise
