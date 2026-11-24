from collections.abc import Callable
from datetime import datetime, timedelta

from autotrading.application.flows.ports import ClockPort, CycleWaitPort
from autotrading.domain.errors import AutotradingError

# Five more calls after the first, after 5, 15, 30, 60 and 120 seconds, as the owner asked ("Riprova sempre"): an
# exchange down a few minutes is up again within the cycle, one that stays down fails the cycle (ADR
# errori-temporanei-ritentati-in-ogni-passo-del-ciclo, ADR ritentativo-del-ciclo-entro-meta-dell-intervallo).
RETRY_PAUSES_SECONDS = (5.0, 15.0, 30.0, 60.0, 120.0)

type FailedAttemptListener = Callable[[int, AutotradingError], None]


class TransientRetry:
    """The one policy of the cycle for a temporary error: the call is made again in the same cycle (ADR
    errori-temporanei-ritentati-in-ogni-passo-del-ciclo).

    An error the base error calls permanent comes out at once (R1.2.4); a temporary one is called again after each
    pause, and the last one comes out when no attempt went through. Every failed attempt is told, with its number, to
    whom the caller names: the record of the cycle shows them.

    A new attempt starts only if, after its pause, the clock is still within the limit of the cycle: half its interval
    from its planned instant, which the cycle sets when it starts (ADR
    ritentativo-del-ciclo-entro-meta-dell-intervallo). The composition builds one retry for every cycle; without a
    limit every attempt starts.
    """

    def __init__(self, wait: CycleWaitPort, clock: ClockPort) -> None:
        self._wait = wait
        self._clock = clock
        self._limit: datetime | None = None

    def limit_to(self, limit: datetime) -> None:
        """The last instant a new attempt may start after its pause."""
        self._limit = limit

    def run[T](self, call: Callable[[], T], failed: FailedAttemptListener) -> T:
        for attempt, pause in enumerate(RETRY_PAUSES_SECONDS, start=1):
            try:
                return call()
            except AutotradingError as error:
                failed(attempt, error)
                if error.permanent or not self._starts_in_time(pause):
                    raise
            self._wait.pause(pause)
        try:
            return call()
        except AutotradingError as error:
            failed(len(RETRY_PAUSES_SECONDS) + 1, error)
            raise

    def _starts_in_time(self, pause: float) -> bool:
        if self._limit is None:
            return True
        return self._clock.now() + timedelta(seconds=pause) <= self._limit
