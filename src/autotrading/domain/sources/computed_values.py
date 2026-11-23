"""The values a source computed for the agent, with the ones the history of the market could not give (ADR
parametri-delle-fonti-come-liste-libere): a value without enough history is declared by its name, the others arrive.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

MISSING = "dati_mancanti"


@dataclass(frozen=True, slots=True)
class MissingValue:
    """A value of a list that could not be computed, by the name it would have had, and why."""

    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ComputedValues:
    values: Mapping[str, Decimal | str] = field(default_factory=dict)
    missing: tuple[MissingValue, ...] = ()

    def prefixed(self, prefix: str) -> ComputedValues:
        """The same values and missing ones, every name under the prefix: "breve." for the short timeframe."""
        return ComputedValues(
            {f"{prefix}{name}": value for name, value in self.values.items()},
            tuple(MissingValue(f"{prefix}{each.name}", each.reason) for each in self.missing),
        )

    def __or__(self, other: ComputedValues) -> ComputedValues:
        return ComputedValues({**self.values, **other.values}, (*self.missing, *other.missing))

    def missing_note(self) -> dict[str, str]:
        """What the agent reads of the values that are missing, those with the same reason together; none when nothing
        is missing.
        """
        if not self.missing:
            return {}
        names_of: dict[str, list[str]] = {}
        for each in self.missing:
            names_of.setdefault(each.reason, []).append(each.name)
        return {MISSING: "; ".join(f"{', '.join(names)}: {reason}" for reason, names in names_of.items())}


def short_history(available: int, unit: str) -> str:
    """The reason of a value the history cannot give: "storico di 40 giorni chiusi"."""
    return f"storico di {available} {unit}"
