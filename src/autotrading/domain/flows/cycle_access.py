from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CycleAccess:
    """The opened credentials a cycle reads its account with, proving they still work on the exchange (R1.2.4).

    Never shown in answers, logs or errors, so the representation masks address and secret (R0.2.3).
    """

    account_address: str = field(repr=False)
    secret_key: str = field(repr=False)
