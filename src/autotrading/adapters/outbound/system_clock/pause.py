import time


class SystemClockPauseAdapter:
    """Waits on the machine before the use case asks the model again (ADR ritentativo-del-modello-nel-ciclo) and
    before a step of the cycle calls its port again (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo).

    Waiting holds only the thread of the cycle that asked: the cycles of the other flows run on.
    """

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)
