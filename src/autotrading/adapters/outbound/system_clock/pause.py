import time


class SystemClockPauseAdapter:
    """Waits on the machine before the use case asks the model again (ADR ritentativo-del-modello-nel-ciclo).

    Waiting holds only the thread of the cycle that asked: the cycles of the other flows run on.
    """

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)
