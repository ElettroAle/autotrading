import logging
import threading
from collections.abc import Callable

from autotrading.domain.errors import AutotradingError

operations = logging.getLogger("autotrading.cycles")


class ThreadCycleLauncherAdapter:
    """Runs every cycle in a thread of its own, so a slow flow never delays another (R1.2.1, ADR 0042).

    The cycle records its own failures; an error that still comes out of it, a permanent one, is logged here and
    never reaches the loop that plans the cycles.
    """

    def launch(self, task: Callable[[], object]) -> None:
        threading.Thread(target=_run, args=(task,), name="cycle", daemon=True).start()


def _run(task: Callable[[], object]) -> None:
    try:
        task()
    except AutotradingError as error:
        operations.warning("ciclo interrotto da un errore permanente", extra={"error": str(error)})
