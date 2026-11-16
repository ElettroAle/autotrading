from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtectionNote:
    """What the cycle records of the protection of a position: a level changed, a protection the exchange refused
    (R3.1.2).
    """

    asset: str
    text: str
