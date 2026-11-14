from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CredentialField:
    """One datum an exchange asks to operate an account, as its adapter declares it (R2.3.9, ADR 0158).

    A secret field is never shown in clear; the other fields together tell which account on the exchange it is.
    """

    name: str
    label: str
    secret: bool
