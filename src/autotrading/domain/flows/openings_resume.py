from enum import StrEnum


class OpeningsResume(StrEnum):
    """How the openings of a flow suspended for maximum loss resume (R3.2.2).

    By hand unless the user chooses otherwise: the openings resume when the user confirms. The next day they resume on
    their own at 00:00 UTC of the day after the suspension, and the user may still confirm before.
    """

    MANUAL = "manual"
    NEXT_DAY = "next_day"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {OpeningsResume.MANUAL: "manuale", OpeningsResume.NEXT_DAY: "il giorno dopo"}
