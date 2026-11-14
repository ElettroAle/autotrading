from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderKeyField:
    """One datum a provider of models asks with its key, as the adapter of its gateway declares it (R2.3.9, ADR 0159).

    A secret field is never shown in clear.
    """

    name: str
    label: str
    secret: bool


# What every provider asked before the fields were declared, and what a key sealed then holds (ADR 0159).
API_KEY_FIELD = ProviderKeyField("api_key", "Chiave API", secret=True)
