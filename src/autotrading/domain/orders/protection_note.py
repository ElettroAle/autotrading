from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtectionNote:
    """What the cycle records of the protection of a position: a level changed, a protection the exchange refused
    (R3.1.2).
    """

    asset: str
    text: str
    # A protection the exchange refused: the stop that follows the price tells it to the next cycle (R5.5.1).
    refused: bool = False
